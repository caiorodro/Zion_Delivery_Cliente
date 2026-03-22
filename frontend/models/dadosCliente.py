from dataclasses import dataclass


@dataclass
class DadosCliente:
    NOME_CLIENTE: str = ""
    CPF: str = ""
    TELEFONE: str = ""
    CPF_NO_CUPOM: bool = False
