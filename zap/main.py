"""Ponto de entrada do bot de WhatsApp do lojista."""
from __future__ import annotations

import logging
import config

from whatsapp_bot import AutoReplyBot

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )


def main() -> None:
    setup_logging()

    bot = AutoReplyBot(
        reply_message=config.AUTO_REPLY_MESSAGE,
        poll_seconds=config.POLL_SECONDS,
        min_seconds_between_replies_per_chat=config.MIN_SECONDS_BETWEEN_REPLIES_PER_CHAT,
    )
    bot.start()


if __name__ == "__main__":
    main()
