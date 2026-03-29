"""
Configurações do robô de integração Zion Delivery → PDV.
Ajuste as variáveis abaixo conforme o ambiente.
"""

# ── API Zion Delivery (fonte dos pedidos pendentes) ──────────────────────────
URL_ZION = "https://ziondelivery.app.br/"
#URL_ZION = "http://127.0.0.1:8000/"

# ── API PDV Zion (destino - sistema interno) ─────────────────────────────────
# TODO: preencha com a URL correta do PDV
URL_PDV = "http://localhost:8000"

# Endpoint de criação de pedido no PDV
ENDPOINT_PEDIDO_PDV = "/pedidos/robo"         # TODO: confirmar rota correta do PDV

# ── Parâmetros fixos de negócio ───────────────────────────────────────────────
ID_CAIXA = 1
ID_TRIBUTO_PADRAO = 1
STATUS_PEDIDO_ACEITO = 8                    # 8 = pedido aceito/lançado no PDV

# ── Controle do loop de polling ───────────────────────────────────────────────
INTERVALO_CONSULTA_SEGUNDOS = 30            # frequência de consulta aos pedidos pendentes
