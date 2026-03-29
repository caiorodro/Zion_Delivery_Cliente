"""
Dataclasses que representam a resposta de GET /pedidos/pendentes (API Zion Delivery).
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ItemPedidoZion:
    ID_PRODUTO: int
    DESCRICAO_PRODUTO: str
    QTDE: float
    PRECO_UNITARIO: float
    TOTAL_ITEM: float
    OBS_ITEM: str = ""
    ID_GRADE: Optional[int] = None
    CODIGO_WABIZ: str = ""


@dataclass
class DadosClienteZion:
    NOME_CLIENTE: str
    CPF: str = ""
    TELEFONE: str = ""


@dataclass
class EnderecoEntregaZion:
    RUA: str
    NUMERO: str
    COMPLEMENTO: str
    CEP: str
    BAIRRO: str
    CIDADE: str
    UF: str
    OBS_ENTREGADOR: str = ""


@dataclass
class PagamentoPedidoZion:
    FORMA_PAGAMENTO: str
    TROCO_PARA: float = 0.0


@dataclass
class PedidoZion:
    NUMERO_PEDIDO: int
    STATUS_PEDIDO: int
    DESCRICAO_STATUS: str
    DATA_HORA: str
    DADOS_CLIENTE: DadosClienteZion
    ENDERECO_ENTREGA: EnderecoEntregaZion
    PAGAMENTO: PagamentoPedidoZion
    ITEMS: List[ItemPedidoZion]
    TAXA_ENTREGA: float = 0.0
    TOTAL_PRODUTOS: float = 0.0
    TOTAL_PEDIDO: float = 0.0
    OBS_PEDIDO: str = ""
    ORIGEM: str = "Delivery próprio"


def pedido_zion_from_dict(data: dict) -> PedidoZion:
    """Converte um dict (parsing do JSON) em PedidoZion."""
    cliente = DadosClienteZion(
        NOME_CLIENTE=data["DADOS_CLIENTE"]["NOME_CLIENTE"],
        CPF=data["DADOS_CLIENTE"].get("CPF", ""),
        TELEFONE=data["DADOS_CLIENTE"].get("TELEFONE", ""),
    )
    endereco = EnderecoEntregaZion(
        RUA=data["ENDERECO_ENTREGA"]["RUA"],
        NUMERO=data["ENDERECO_ENTREGA"]["NUMERO"],
        COMPLEMENTO=data["ENDERECO_ENTREGA"].get("COMPLEMENTO", ""),
        CEP=data["ENDERECO_ENTREGA"]["CEP"],
        BAIRRO=data["ENDERECO_ENTREGA"]["BAIRRO"],
        CIDADE=data["ENDERECO_ENTREGA"]["CIDADE"],
        UF=data["ENDERECO_ENTREGA"]["UF"],
        OBS_ENTREGADOR=data["ENDERECO_ENTREGA"].get("OBS_ENTREGADOR", ""),
    )
    pagamento = PagamentoPedidoZion(
        FORMA_PAGAMENTO=data["PAGAMENTO"]["FORMA_PAGAMENTO"],
        TROCO_PARA=data["PAGAMENTO"].get("TROCO_PARA", 0.0),
    )
    items = [
        ItemPedidoZion(
            ID_PRODUTO=it["ID_PRODUTO"],
            DESCRICAO_PRODUTO=it["DESCRICAO_PRODUTO"],
            QTDE=it["QTDE"],
            PRECO_UNITARIO=it["PRECO_UNITARIO"],
            TOTAL_ITEM=it["TOTAL_ITEM"],
            OBS_ITEM=it.get("OBS_ITEM", ""),
            ID_GRADE=it.get("ID_GRADE"),
            CODIGO_WABIZ=it.get("CODIGO_WABIZ", ""),
        )
        for it in data["ITEMS"]
    ]
    return PedidoZion(
        NUMERO_PEDIDO=data["NUMERO_PEDIDO"],
        STATUS_PEDIDO=data["STATUS_PEDIDO"],
        DESCRICAO_STATUS=data.get("DESCRICAO_STATUS", ""),
        DATA_HORA=data["DATA_HORA"],
        DADOS_CLIENTE=cliente,
        ENDERECO_ENTREGA=endereco,
        PAGAMENTO=pagamento,
        ITEMS=items,
        TAXA_ENTREGA=data.get("TAXA_ENTREGA", 0.0),
        TOTAL_PRODUTOS=data.get("TOTAL_PRODUTOS", 0.0),
        TOTAL_PEDIDO=data.get("TOTAL_PEDIDO", 0.0),
        OBS_PEDIDO=data.get("OBS_PEDIDO", ""),
        ORIGEM=data.get("ORIGEM", "Delivery próprio"),
    )
