from dataclasses import dataclass
from typing import Optional


@dataclass
class ListaProduto:
    ID_PRODUTO: int
    DESCRICAO_PRODUTO: str
    PRECO_DELIVERY: float
    ID_FAMILIA: int
    PRODUTO_ATIVO: int
    FOTO_PRODUTO: str = ""
