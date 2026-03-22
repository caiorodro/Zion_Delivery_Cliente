from dataclasses import dataclass


@dataclass
class Endereco:
    id: int
    cep: str
    uf: str
    cidade: str
    bairro: str
    logradouro: str
