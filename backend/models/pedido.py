from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ItemPedido:
    ID_PRODUTO: int
    DESCRICAO_PRODUTO: str
    QTDE: int
    PRECO_UNITARIO: float
    TOTAL_ITEM: float
    OBS_ITEM: str = ""
    ID_GRADE: Optional[int] = None


@dataclass
class EnderecoEntrega:
    RUA: str
    NUMERO: str
    COMPLEMENTO: str
    CEP: str
    BAIRRO: str
    CIDADE: str
    UF: str
    OBS_ENTREGADOR: str


@dataclass
class DadosCliente:
    NOME_CLIENTE: str
    CPF: str = ""
    TELEFONE: str = ""


@dataclass
class PagamentoPedido:
    FORMA_PAGAMENTO: str          # CARTAO | DINHEIRO | PIX
    TROCO_PARA: float = 0.0


@dataclass
class Pedido:
    DADOS_CLIENTE: DadosCliente
    ENDERECO_ENTREGA: EnderecoEntrega
    ITEMS: List[ItemPedido]
    PAGAMENTO: PagamentoPedido
    TAXA_ENTREGA: float
    TOTAL_PRODUTOS: float
    TOTAL_PEDIDO: float
    OBS_PEDIDO: str = ""
    ORIGEM: str = "Delivery próprio"
    STATUS_PEDIDO: int = 0        # 0=Aguardando, 1=Aceito, 2=Em preparo, 3=Saiu, 4=Entregue


@dataclass
class StatusPedido:
    NUMERO_PEDIDO: int
    STATUS_PEDIDO: int
    DESCRICAO_STATUS: str
    DATA_HORA: str
