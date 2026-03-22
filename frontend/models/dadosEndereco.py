from dataclasses import dataclass


@dataclass
class DadosEndereco:
    RUA: str = ""
    NUMERO: str = ""
    COMPLEMENTO: str = ""
    CEP: str = ""
    BAIRRO: str = ""
    CIDADE: str = ""
    UF: str = ""
    OBS_ENTREGADOR: str = ""
