from dataclasses import dataclass


@dataclass
class GradeProduto:
    ID_PRODUTO: int
    QTDE_INICIAL: int
    QTDE_FINAL: int
    PRECO_VENDA: float = 0.0
