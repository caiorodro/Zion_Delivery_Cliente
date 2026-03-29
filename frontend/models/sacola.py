from dataclasses import dataclass, field
from typing import List

from frontend.models.dadosCliente import DadosCliente
from frontend.models.dadosEndereco import DadosEndereco
from frontend.models.itemPedido import ItemPedido


@dataclass
class PagamentoPedido:
    FORMA_PAGAMENTO: str = ""   # CARTAO | DINHEIRO | PIX
    TROCO_PARA: float = 0.0


@dataclass
class Sacola:
    DADOS_CLIENTE: DadosCliente = field(default_factory=DadosCliente)
    DADOS_ENDERECO: DadosEndereco = field(default_factory=DadosEndereco)
    ITEMS: List[ItemPedido] = field(default_factory=list)
    PAGAMENTO: PagamentoPedido = field(default_factory=PagamentoPedido)
    TAXA_ENTREGA: float = 5.00
    OBS_PEDIDO: str = ""

    @property
    def total_produtos(self) -> float:
        return sum(i.TOTAL_ITEM for i in self.ITEMS)

    @property
    def total_pedido(self) -> float:
        return self.total_produtos + self.TAXA_ENTREGA

    def to_dict(self) -> dict:
        return {
            "DADOS_CLIENTE": {
                "NOME_CLIENTE": self.DADOS_CLIENTE.NOME_CLIENTE,
                "CPF": self.DADOS_CLIENTE.CPF if self.DADOS_CLIENTE.CPF_NO_CUPOM else "",
                "TELEFONE": self.DADOS_CLIENTE.TELEFONE,
            },
            "ENDERECO_ENTREGA": {
                "RUA": self.DADOS_ENDERECO.RUA,
                "NUMERO": self.DADOS_ENDERECO.NUMERO,
                "COMPLEMENTO": self.DADOS_ENDERECO.COMPLEMENTO,
                "CEP": self.DADOS_ENDERECO.CEP,
                "BAIRRO": self.DADOS_ENDERECO.BAIRRO,
                "CIDADE": self.DADOS_ENDERECO.CIDADE,
                "UF": self.DADOS_ENDERECO.UF,
                "OBS_ENTREGADOR": self.DADOS_ENDERECO.OBS_ENTREGADOR,
            },
            "ITEMS": [
                {
                    "ID_PRODUTO": it.ID_PRODUTO,
                    "CODIGO_WABIZ": it.CODIGO_WABIZ,
                    "DESCRICAO_PRODUTO": it.DESCRICAO_PRODUTO,
                    "QTDE": it.QTDE,
                    "PRECO_UNITARIO": it.PRECO_UNITARIO,
                    "TOTAL_ITEM": it.TOTAL_ITEM,
                    "OBS_ITEM": it.OBS_ITEM,
                    "ID_GRADE": it.ID_GRADE,
                }
                for it in self.ITEMS
            ],
            "PAGAMENTO": {
                "FORMA_PAGAMENTO": self.PAGAMENTO.FORMA_PAGAMENTO,
                "TROCO_PARA": self.PAGAMENTO.TROCO_PARA,
            },
            "TAXA_ENTREGA": self.TAXA_ENTREGA,
            "TOTAL_PRODUTOS": self.total_produtos,
            "TOTAL_PEDIDO": self.total_pedido,
            "OBS_PEDIDO": self.OBS_PEDIDO,
            "ORIGEM": "Delivery próprio",
        }
