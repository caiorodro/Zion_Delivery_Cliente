"""Configuracoes do bot de WhatsApp (resposta automatica para novos contatos)."""
from __future__ import annotations

import os

# URL da loja no delivery.
DELIVERY_LINK = os.getenv("ZAP_DELIVERY_LINK", "https://lojabeervt.ziondelivery.app.br/")

# Intervalo (segundos) de verificacao de novas conversas nao lidas.
POLL_SECONDS = int(os.getenv("ZAP_POLL_SECONDS", "6"))

# Evita enviar resposta repetida para o mesmo contato em curto prazo.
MIN_SECONDS_BETWEEN_REPLIES_PER_CHAT = int(
    os.getenv("ZAP_MIN_SECONDS_BETWEEN_REPLIES", "21600")  # 6 horas
)

# Diretório opcional para persistir sessao do Chrome e nao pedir QR sempre.
CHROME_USER_DATA_DIR = os.getenv("ZAP_CHROME_USER_DATA_DIR", "")

# Se houver varios perfis no Chrome, informe o nome (ex.: "Profile 2").
CHROME_PROFILE_DIRECTORY = os.getenv("ZAP_CHROME_PROFILE_DIRECTORY", "")

AUTO_REPLY_MESSAGE = os.getenv(
    "ZAP_AUTO_REPLY_MESSAGE",
    (
        "Ola! Seja muito bem-vindo(a) a nossa loja! 👋\\n\\n"
        "Para fazer seu pedido de forma rapida, clique no link abaixo:\\n"
        "https://lojabeervt.ziondelivery.app.br/\\n\\n"
        "Nosso cardapio completo esta no app. Esperamos voce! 🍻"
    ),
)
