from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import json

from cfg.config import Config
from base.authentication import Authentication
from views.produto import ProdutoView
from views.endereco import EnderecoView
from views.frete import FreteView
from views.pedido import PedidoView
from models.pedido import (
    Pedido, DadosCliente, EnderecoEntrega, ItemPedido, PagamentoPedido
)

app = FastAPI(
    title="Zion Delivery API",
    version="1.0.0",
    description="API para o app de delivery Zion"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

@app.get("/auth/token", tags=["Auth"])
def get_token():
    token = Authentication.generate_token()
    return {"token": token}


# ─────────────────────────────────────────────
# PRODUTOS / FAMÍLIAS / GRADES
# ─────────────────────────────────────────────

@app.get("/produtos", tags=["Produtos"])
async def listar_produtos():
    view = ProdutoView()
    return await view.get_all_produtos()


@app.patch("/produtos/{id_produto}", tags=["Produtos"])
async def atualizar_produto(id_produto: int, body: dict):
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body da requisição não pode ser vazio"
        )

    view = ProdutoView()

    try:
        result = await view.update_produto(id_produto, body)
    except ValueError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ex)
        )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ex)
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )

    return result


@app.get("/familias", tags=["Produtos"])
async def listar_familias():
    view = ProdutoView()
    return await view.get_all_familias()


@app.get("/grades", tags=["Produtos"])
async def listar_grades():
    view = ProdutoView()
    return await view.get_all_grades()


# ─────────────────────────────────────────────
# ENDEREÇOS
# ─────────────────────────────────────────────

@app.get("/enderecos/ufs", tags=["Endereços"])
async def listar_ufs():
    view = EnderecoView()
    return await view.get_ufs()


@app.get("/enderecos/cidades/{uf}", tags=["Endereços"])
async def listar_cidades(uf: str):
    view = EnderecoView()
    return await view.get_cidades_por_uf(uf.upper())


@app.get("/enderecos/pesquisar", tags=["Endereços"])
async def pesquisar_endereco(uf: str, cidade: str, termo: str):
    if len(termo.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O termo de pesquisa deve ter pelo menos 2 caracteres"
        )
    view = EnderecoView()
    return await view.pesquisar_endereco(uf, cidade, termo)


@app.get("/enderecos/cep/{cep}", tags=["Endereços"])
async def buscar_por_cep(cep: str):
    view = EnderecoView()
    return await view.buscar_por_cep(cep)


@app.get("/fretes/faixa", tags=["Frete"])
async def buscar_frete_por_distancia(distancia_km: float):
    if distancia_km < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A distância deve ser maior ou igual a zero"
        )

    view = FreteView()
    result = await view.get_faixa_por_distancia(distancia_km)
    if result is None:
        return {}
    return result


# ─────────────────────────────────────────────
# PEDIDOS
# ─────────────────────────────────────────────

@app.post("/pedidos", tags=["Pedidos"])
def criar_pedido(body: dict):
    """Recebe o JSON do pedido e grava no banco. Operação síncrona."""
    try:
        dados_cliente = DadosCliente(
            NOME_CLIENTE=body["DADOS_CLIENTE"]["NOME_CLIENTE"],
            CPF=body["DADOS_CLIENTE"].get("CPF", ""),
            TELEFONE=body["DADOS_CLIENTE"].get("TELEFONE", ""),
        )
        endereco = EnderecoEntrega(
            RUA=body["ENDERECO_ENTREGA"]["RUA"],
            NUMERO=body["ENDERECO_ENTREGA"]["NUMERO"],
            COMPLEMENTO=body["ENDERECO_ENTREGA"].get("COMPLEMENTO", ""),
            CEP=body["ENDERECO_ENTREGA"]["CEP"],
            BAIRRO=body["ENDERECO_ENTREGA"]["BAIRRO"],
            CIDADE=body["ENDERECO_ENTREGA"]["CIDADE"],
            UF=body["ENDERECO_ENTREGA"]["UF"],
            OBS_ENTREGADOR=body["ENDERECO_ENTREGA"].get("OBS_ENTREGADOR", ""),
        )
        items = [
            ItemPedido(
                ID_PRODUTO=it["ID_PRODUTO"],
                DESCRICAO_PRODUTO=it["DESCRICAO_PRODUTO"],
                QTDE=it["QTDE"],
                PRECO_UNITARIO=it["PRECO_UNITARIO"],
                TOTAL_ITEM=it["TOTAL_ITEM"],
                OBS_ITEM=it.get("OBS_ITEM", ""),
                ID_GRADE=it.get("ID_GRADE"),
            )
            for it in body["ITEMS"]
        ]
        pagamento = PagamentoPedido(
            FORMA_PAGAMENTO=body["PAGAMENTO"]["FORMA_PAGAMENTO"],
            TROCO_PARA=body["PAGAMENTO"].get("TROCO_PARA", 0.0),
        )
        pedido = Pedido(
            DADOS_CLIENTE=dados_cliente,
            ENDERECO_ENTREGA=endereco,
            ITEMS=items,
            PAGAMENTO=pagamento,
            TAXA_ENTREGA=body.get("TAXA_ENTREGA", 0.0),
            TOTAL_PRODUTOS=body.get("TOTAL_PRODUTOS", 0.0),
            TOTAL_PEDIDO=body.get("TOTAL_PEDIDO", 0.0),
            OBS_PEDIDO=body.get("OBS_PEDIDO", ""),
            ORIGEM=body.get("ORIGEM", "Delivery próprio"),
        )

        view = PedidoView()
        resultado = view.gravar_pedido(pedido)
        return resultado

    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo obrigatório ausente: {ke}"
        )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ex)
        )


@app.get("/pedidos/pendentes", tags=["Pedidos"])
async def listar_pedidos_pendentes():
    """Retorna todos os pedidos com STATUS_PEDIDO = 0 (Aguardando confirmação)."""
    view = PedidoView()
    return await view.get_pedidos_pendentes()


@app.patch("/pedidos/{numero_pedido}/aceitar", tags=["Pedidos"])
async def aceitar_pedido(numero_pedido: int):
    """Atualiza STATUS_PEDIDO de 0 para 1 (Pedido aceito)."""
    view = PedidoView()
    result = await view.aceitar_pedido(numero_pedido)
    if result.get("STATUS_PEDIDO") == -1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["DESCRICAO_STATUS"],
        )
    return result


@app.get("/pedidos/{numero_pedido}/status", tags=["Pedidos"])
async def status_pedido(numero_pedido: int):
    view = PedidoView()
    return await view.get_status_pedido(numero_pedido)


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Zion Delivery API"}
