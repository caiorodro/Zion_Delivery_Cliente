"""
Robô de integração Zion Delivery → PDV.

Fluxo:
  1. Consulta GET /pedidos/pendentes na API Zion a cada INTERVALO_CONSULTA_SEGUNDOS.
  2. Para cada pedido novo (ainda não processado), converte para o formato PDV.
  3. Envia POST para a API do PDV.
  4. Aceita o pedido no Zion via PATCH /pedidos/{numero}/aceitar.
  5. Registra o NUMERO_PEDIDO processado para não reprocessar.

Uso: python -m robot.main
"""
import json
import logging
import time

import requests

from config import (
    URL_ZION,
    URL_PDV,
    ENDPOINT_PEDIDO_PDV,
    INTERVALO_CONSULTA_SEGUNDOS,
)
from models.pedido_zion import pedido_zion_from_dict
from mapper import mapear_pedido

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
log = logging.getLogger(__name__)

# Pedidos já processados nesta sessão (evita reprocessamento enquanto o robô roda)
_processados: set[int] = set()

def buscar_pedidos_pendentes() -> list[dict]:
    """Retorna a lista de pedidos pendentes da API Zion."""
    url = f"{URL_ZION}/pedidos/pendentes"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

def enviar_para_pdv(payload: dict) -> dict:
    """Envia o pedido mapeado para a API do PDV e retorna a resposta."""
    url = f"{URL_PDV}{ENDPOINT_PEDIDO_PDV}"
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def aceitar_pedido_zion(numero_pedido: int) -> None:
    """Marca o pedido como aceito na API Zion."""
    url = f"{URL_ZION}/pedidos/{numero_pedido}/aceitar"
    response = requests.patch(url, timeout=10)
    response.raise_for_status()

def processar_pedido(pedido_dict: dict) -> None:
    """Processa um único pedido: converte, envia ao PDV e aceita no Zion."""
    numero = pedido_dict["NUMERO_PEDIDO"]

    if numero in _processados:
        return

    log.info(f"Processando pedido #{numero}...")

    # 1. Deserializar
    pedido_zion = pedido_zion_from_dict(pedido_dict)

    # 2. Mapear para o formato PDV
    request_pdv = mapear_pedido(pedido_zion)
    payload = request_pdv.to_dict()

    log.debug("Payload PDV:\n%s", json.dumps(payload, indent=2, ensure_ascii=False))

    # 3. Enviar ao PDV
    resposta_pdv = enviar_para_pdv(payload)
    log.info(f"Pedido #{numero} enviado ao PDV. Resposta: {resposta_pdv}")

    # 4. Aceitar no Zion
    aceitar_pedido_zion(numero)
    log.info(f"Pedido #{numero} aceito no Zion Delivery.")

    # 5. Marcar como processado
    _processados.add(numero)


def ciclo() -> None:
    """Executa um ciclo completo de consulta e processamento."""
    try:
        pedidos = buscar_pedidos_pendentes()
        if not pedidos:
            return

        log.info(f"{len(pedidos)} pedido(s) pendente(s) encontrado(s).")
        for pedido_dict in pedidos:
            try:
                processar_pedido(pedido_dict)
            except Exception as ex:
                numero = pedido_dict.get("NUMERO_PEDIDO", "?")
                log.error(f"Erro ao processar pedido #{numero}: {ex}", exc_info=True)

    except requests.RequestException as ex:
        log.error(f"Erro na comunicação com a API Zion: {ex}")


def main() -> None:
    log.info("Robô Zion → PDV iniciado. Intervalo: %ds", INTERVALO_CONSULTA_SEGUNDOS)
    while True:
        ciclo()
        time.sleep(INTERVALO_CONSULTA_SEGUNDOS)


if __name__ == "__main__":
    main()
