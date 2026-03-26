"""
Dataclasses que representam o body do POST para a API do PDV Zion (sistema interno).
Campos e valores seguem o contrato do endpoint de criação de pedido do PDV.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class PedidoPDV:
    NUMERO_PEDIDO: int
    DATA_HORA: str
    DATA_ENTREGA: str
    DATA_HORA_AGENDA: str
    TEMPO_ENTREGA: str
    TEMPO_RETIRADA_LOJA: str
    TEMPO_MOTOBOY_CAMINHO: str
    ID_CLIENTE: int
    ID_ENDERECO: int
    CPF: str
    IE: str
    NOME_CLIENTE: str
    ENDERECO_CLIENTE: str
    BAIRRO_CLIENTE: str
    CEP: str
    TELEFONE_CLIENTE: str
    LATITUDE: float
    LONGITUDE: float
    ORIGEM: str
    ID_CAIXA: int
    STATUS_PEDIDO: int
    NUMERO_PESSOAS: int
    NUMERO_VENDA: int
    TIPO_ADICIONAL: str
    TOTAL_PRODUTOS: float
    TROCO: float
    DESCONTO: float
    ADICIONAL: float
    TAXA_ENTREGA: float
    TOTAL_PEDIDO: float
    MOTIVO_DEVOLUCAO: str
    ID_TRANSPORTE: int
    INFO_ADICIONAL: str
    NUMERO_PEDIDO_ZE_DELIVERY: int
    NUMERO_PEDIDO_DELIVERY: int
    NUMERO_PEDIDO_LALAMOVE: str
    NUMERO_PEDIDO_IFOOD: str
    ID_PEDIDO_IFOOD: str
    TIPO_PEDIDO_IFOOD: int
    CODIGO_IDENTIFICACAO_IFOOD: str
    ORDER_NUMBER_GOOMER: int
    ID_PEDIDO_GOOMER: int
    ORDER_NUMBER_WABIZ: int
    INTERNAL_KEY_WABIZ: str
    ORDER_NUMBER_RAPPI: int
    REQUEST_ID_FATTORINO: str
    INTERNAL_KEY_ZION: str
    MOTIVO_CANCELAMENTO: str
    COMENTARIOS_AVALIACAO: str
    NOTA_AVALIACAO: int
    ORDEM_ROTEIRO: int
    TEMPO_ATENDIMENTO_ROBO: str
    TEMPO_ENTREGA_PEDIDO: str
    ID_PEDIDO_LOCAL: int
    ID_TERMINAL: int


@dataclass
class ItemPedidoPDV:
    NUMERO_ITEM: int
    NUMERO_PEDIDO: int
    ID_PRODUTO: str
    CODIGO_PRODUTO: str
    DESCRICAO_PRODUTO: str
    QTDE: float
    PRECO_UNITARIO: float
    VALOR_TOTAL: float
    ID_TRIBUTO: int
    OBS_ITEM: str
    ID_ITEM_LOCAL: int
    ID_TERMINAL: int


@dataclass
class PagamentoPDV:
    ID_PAGAMENTO: int
    NUMERO_PEDIDO: int
    DATA_HORA: str
    FORMA_PAGTO: str
    VALOR_PAGO: float
    ID_CAIXA: int
    ORIGEM: str
    ID_PAGAMENTO_LOCAL: int
    ID_TERMINAL: int
    CODIGO_NSU: str
    VALOR_PAGO_STONE: float
    DATA_AUTORIZACAO: str
    BANDEIRA: str


@dataclass
class ImpressaoPedidoPDV:
    IMPRESSAO_NAO_FISCAL: int = 0
    IMPRESSAO_FISCAL: int = 0
    NUMERO_IMPRESSORA: int = 0


@dataclass
class RequestPedidoPDV:
    """Representa o body completo do POST para o PDV."""
    pedido: PedidoPDV
    itemsPedido: List[ItemPedidoPDV]
    pagamento: List[PagamentoPDV]
    impressaoPedido: ImpressaoPedidoPDV

    def to_dict(self) -> dict:
        """Serializa para dict pronto para json.dumps / requests.post(json=...)."""
        import dataclasses
        return {
            "pedido": dataclasses.asdict(self.pedido),
            "itemsPedido": [dataclasses.asdict(it) for it in self.itemsPedido],
            "pagamento": [dataclasses.asdict(pg) for pg in self.pagamento],
            "impressaoPedido": dataclasses.asdict(self.impressaoPedido),
        }
