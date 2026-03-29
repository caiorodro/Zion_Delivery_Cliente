from dataclasses import dataclass
from typing import Optional


@dataclass
class Produto:
    ID_PRODUTO: int
    DESCRICAO_PRODUTO: str
    PRECO_DELIVERY: float
    PRODUTO_ATIVO: int
    FOTO_PRODUTO: Optional[str]
    CODIGO_WABIZ: str = ""


@dataclass
class ProdutoCreate:
    CODIGO_PRODUTO: str
    CODIGO_PRODUTO_PDV: str
    DESCRICAO_PRODUTO: str
    PRECO_BALCAO: float
    PRECO_DELIVERY: float
    ID_TRIBUTO: int
    ID_FAMILIA: int
    ID_EMPRESA: int
    PRODUTO_ATIVO: int
    CODIGO_WABIZ: str
