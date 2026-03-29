from dataclasses import dataclass


@dataclass
class ListaProduto:
    ID_PRODUTO: int
    DESCRICAO_PRODUTO: str
    PRECO_DELIVERY: float
    PRODUTO_ATIVO: int
    FOTO_PRODUTO: str = ""
    CODIGO_WABIZ: str = ""
