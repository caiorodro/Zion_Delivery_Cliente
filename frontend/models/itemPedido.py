from dataclasses import dataclass
from typing import Optional


@dataclass
class ItemPedido:
    ID_PRODUTO: int
    DESCRICAO_PRODUTO: str
    QTDE: int
    PRECO_UNITARIO: float
    TOTAL_ITEM: float
    OBS_ITEM: str = ""
    ID_GRADE: Optional[int] = None
