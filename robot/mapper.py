"""
Converte um PedidoZion (resposta de GET /pedidos/pendentes)
em um RequestPedidoPDV (body do POST para o PDV Zion).

TODO: revise os mapeamentos marcados com # TODO para confirmar
      os valores corretos com a equipe.
"""
from datetime import datetime

from models.pedido_zion import PedidoZion
from models.pedido_pdv import (
    RequestPedidoPDV,
    PedidoPDV,
    ItemPedidoPDV,
    PagamentoPDV,
    ImpressaoPedidoPDV,
)
from config import ID_CAIXA, ID_TRIBUTO_PADRAO, STATUS_PEDIDO_ACEITO


_FMT_ISO = "%Y-%m-%dT%H:%M:%S"
_FMT_PDV = "%d/%m/%Y %H:%M"


def _fmt_data(iso_str: str) -> str:
    """Converte '2026-03-26T08:56:05' -> '26/03/2026 08:56'."""
    try:
        dt = iso_str.replace('T', ' ').replace('Z', '')
        return dt
    except (ValueError, TypeError):
        return datetime.now().strftime(_FMT_PDV)


def _endereco_completo(endereco) -> str:
    """Monta string de endereço no formato 'RUA, NUMERO - COMPLEMENTO - CEP'."""
    partes = [f"{endereco.RUA}, {endereco.NUMERO}"]
    if endereco.COMPLEMENTO:
        partes.append(endereco.COMPLEMENTO)
    if endereco.CEP:
        partes.append(endereco.CEP)
    return " - ".join(partes)


def _cpf(cpf: str) -> str:
    return cpf.strip() if cpf.strip() else "ISENTO"


def _troco(total_pedido: float, troco_para: float) -> float:
    """
    Calcula o troco (valor de volta ao cliente).
    Se troco_para > total_pedido, o troco é a diferença; senão 0.
    TODO: valide se a lógica de troco atende todos os cenários de pagamento.
    """
    if troco_para > total_pedido:
        return round(troco_para - total_pedido, 2)
    return 0.0


def _valor_pago(total_pedido: float, troco_para: float) -> float:
    """
    Valor entregue pelo cliente.
    Se troco_para foi informado (> 0), usa ele; senão usa o total do pedido.
    TODO: valide cenários de múltiplas formas de pagamento.
    """
    return troco_para if troco_para > 0 else total_pedido


def mapear_pedido(pedido: PedidoZion) -> RequestPedidoPDV:
    """Converte PedidoZion -> RequestPedidoPDV."""
    data_hora_fmt = _fmt_data(pedido.DATA_HORA)

    # ── Pedido ──────────────────────────────────────────────────────────────
    pedido_pdv = PedidoPDV(
        NUMERO_PEDIDO=0,                                    # PDV gera o número
        DATA_HORA=data_hora_fmt,
        DATA_ENTREGA=data_hora_fmt,                         # TODO: ajustar se houver janela de entrega
        DATA_HORA_AGENDA=data_hora_fmt,
        TEMPO_ENTREGA="0",
        TEMPO_RETIRADA_LOJA=data_hora_fmt,
        TEMPO_MOTOBOY_CAMINHO=data_hora_fmt,
        ID_CLIENTE=0,                                       # TODO: lookup de cliente se o PDV suportar
        ID_ENDERECO=0,
        CPF=_cpf(pedido.DADOS_CLIENTE.CPF),
        IE="",
        NOME_CLIENTE=pedido.DADOS_CLIENTE.NOME_CLIENTE,
        ENDERECO_CLIENTE=_endereco_completo(pedido.ENDERECO_ENTREGA),
        BAIRRO_CLIENTE=pedido.ENDERECO_ENTREGA.BAIRRO,
        CEP=pedido.ENDERECO_ENTREGA.CEP,
        TELEFONE_CLIENTE=pedido.DADOS_CLIENTE.TELEFONE,
        LATITUDE=0,
        LONGITUDE=0,
        ORIGEM=pedido.ORIGEM,
        ID_CAIXA=ID_CAIXA,
        STATUS_PEDIDO=STATUS_PEDIDO_ACEITO,
        NUMERO_PESSOAS=0,
        NUMERO_VENDA=0,
        TIPO_ADICIONAL="% geral",
        TOTAL_PRODUTOS=pedido.TOTAL_PRODUTOS,
        TROCO=_troco(pedido.TOTAL_PEDIDO, pedido.PAGAMENTO.TROCO_PARA),
        DESCONTO=0.0,
        ADICIONAL=0.0,
        TAXA_ENTREGA=pedido.TAXA_ENTREGA,
        TOTAL_PEDIDO=pedido.TOTAL_PEDIDO,
        MOTIVO_DEVOLUCAO="",
        ID_TRANSPORTE=0,
        INFO_ADICIONAL=pedido.OBS_PEDIDO,
        NUMERO_PEDIDO_ZE_DELIVERY=0,
        NUMERO_PEDIDO_DELIVERY=pedido.NUMERO_PEDIDO,        # referência ao pedido Zion
        NUMERO_PEDIDO_LALAMOVE="",
        NUMERO_PEDIDO_IFOOD="",
        ID_PEDIDO_IFOOD="",
        TIPO_PEDIDO_IFOOD=0,
        CODIGO_IDENTIFICACAO_IFOOD="",
        ORDER_NUMBER_GOOMER=0,
        ID_PEDIDO_GOOMER=0,
        ORDER_NUMBER_WABIZ=0,
        INTERNAL_KEY_WABIZ="",
        ORDER_NUMBER_RAPPI=0,
        REQUEST_ID_FATTORINO="",
        INTERNAL_KEY_ZION=str(pedido.NUMERO_PEDIDO),       # chave de rastreio do pedido Zion
        MOTIVO_CANCELAMENTO="",
        COMENTARIOS_AVALIACAO="",
        NOTA_AVALIACAO=0,
        ORDEM_ROTEIRO=0,
        TEMPO_ATENDIMENTO_ROBO=data_hora_fmt,
        TEMPO_ENTREGA_PEDIDO=data_hora_fmt,
        ID_PEDIDO_LOCAL=0,
        ID_TERMINAL=0,
    )

    # ── Itens ────────────────────────────────────────────────────────────────
    items_pdv = [
        ItemPedidoPDV(
            NUMERO_ITEM=0,
            NUMERO_PEDIDO=0,
            ID_PRODUTO=str(it.ID_PRODUTO),
            CODIGO_PRODUTO="",
            DESCRICAO_PRODUTO=it.DESCRICAO_PRODUTO,
            QTDE=it.QTDE,
            PRECO_UNITARIO=it.PRECO_UNITARIO,
            VALOR_TOTAL=it.TOTAL_ITEM,
            ID_TRIBUTO=ID_TRIBUTO_PADRAO,
            OBS_ITEM=it.OBS_ITEM,
            ID_ITEM_LOCAL=0,
            ID_TERMINAL=0,
        )
        for it in pedido.ITEMS
    ]

    # ── Pagamento ────────────────────────────────────────────────────────────
    valor_pago = _valor_pago(pedido.TOTAL_PEDIDO, pedido.PAGAMENTO.TROCO_PARA)
    pagamento_pdv = [
        PagamentoPDV(
            ID_PAGAMENTO=0,
            NUMERO_PEDIDO=0,
            DATA_HORA=data_hora_fmt,
            FORMA_PAGTO=pedido.PAGAMENTO.FORMA_PAGAMENTO,   # TODO: normalizar se o PDV usa vocabulário diferente
            VALOR_PAGO=valor_pago,
            ID_CAIXA=ID_CAIXA,
            ORIGEM=pedido.ORIGEM,
            ID_PAGAMENTO_LOCAL=0,
            ID_TERMINAL=0,
            CODIGO_NSU="",
            VALOR_PAGO_STONE=valor_pago,
            DATA_AUTORIZACAO="01/01/1901 00:00",
            BANDEIRA="",
        )
    ]

    # ── Impressão ────────────────────────────────────────────────────────────
    impressao = ImpressaoPedidoPDV(
        IMPRESSAO_NAO_FISCAL=0,
        IMPRESSAO_FISCAL=0,
        NUMERO_IMPRESSORA=0,
    )

    return RequestPedidoPDV(
        pedido=pedido_pdv,
        itemsPedido=items_pdv,
        pagamento=pagamento_pdv,
        impressaoPedido=impressao,
    )
