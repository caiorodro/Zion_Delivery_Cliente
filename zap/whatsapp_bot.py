"""Automacao simples do WhatsApp Web usando Selenium."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config

log = logging.getLogger(__name__)

@dataclass
class AutoReplyBot:
    """Bot que responde chats nao lidos com uma mensagem padrao."""

    reply_message: str
    poll_seconds: int
    min_seconds_between_replies_per_chat: int
    _last_reply_by_chat: dict[str, float] = field(default_factory=dict)
    _driver: Chrome | None = None

    def start(self) -> None:
        self._driver = self._build_driver()
        self._open_whatsapp_web()
        self._wait_login()

        log.info("Bot pronto. Monitorando conversas nao lidas...")
        while True:
            self._process_unread_chats()
            time.sleep(self.poll_seconds)

    def _build_driver(self) -> Chrome:
        options = Options()
        options.add_argument("--start-maximized")

        if config.CHROME_USER_DATA_DIR:
            options.add_argument(f"--user-data-dir={config.CHROME_USER_DATA_DIR}")

        if config.CHROME_PROFILE_DIRECTORY:
            options.add_argument(f"--profile-directory={config.CHROME_PROFILE_DIRECTORY}")

        # Selenium Manager (Selenium 4+) resolve automaticamente o driver.
        return webdriver.Chrome(options=options)

    def _open_whatsapp_web(self) -> None:
        assert self._driver is not None
        self._driver.get("https://web.whatsapp.com")

    def _wait_login(self) -> None:
        assert self._driver is not None
        wait = WebDriverWait(self._driver, 120)
        try:
            # O painel de conversas aparece somente apos o login.
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#pane-side"))
            )
            log.info("Login detectado no WhatsApp Web.")
        except TimeoutException as ex:
            raise RuntimeError(
                "Nao foi possivel detectar login no WhatsApp Web. "
                "Escaneie o QR Code e tente novamente."
            ) from ex

    def _process_unread_chats(self) -> None:
        assert self._driver is not None

        unread_rows = self._find_unread_chat_rows()
        if not unread_rows:
            return

        for row in unread_rows:
            try:
                row.click()
                time.sleep(0.8)

                chat_name = self._get_current_chat_name()
                if not self._can_reply(chat_name):
                    continue

                self._send_message(self.reply_message)
                self._last_reply_by_chat[chat_name] = time.time()
                log.info("Resposta enviada para '%s'.", chat_name)
                time.sleep(0.6)
            except Exception as ex:  # pragma: no cover - automacao depende da UI
                log.error("Falha ao responder chat: %s", ex, exc_info=True)

    def _find_unread_chat_rows(self) -> list:
        assert self._driver is not None

        # Tentativa por seletor sem depender de idioma.
        rows = self._driver.find_elements(
            By.XPATH,
            "//div[@id='pane-side']//div[@role='listitem'][.//*[@data-testid='icon-unread-count']]",
        )
        if rows:
            return rows

        # Fallback por aria-label (pt/en), caso o data-testid mude.
        rows = self._driver.find_elements(
            By.XPATH,
            "//div[@id='pane-side']//div[@role='listitem'][.//*[contains(@aria-label, 'nao lida') or contains(@aria-label, 'unread')]]",
        )
        return rows

    def _get_current_chat_name(self) -> str:
        assert self._driver is not None
        try:
            name_el = self._driver.find_element(By.XPATH, "//header//span[@title]")
            chat_name = name_el.get_attribute("title") or "chat_sem_nome"
            return chat_name.strip()
        except NoSuchElementException:
            return "chat_sem_nome"

    def _can_reply(self, chat_name: str) -> bool:
        last_reply = self._last_reply_by_chat.get(chat_name)
        if not last_reply:
            return True

        elapsed = time.time() - last_reply
        return elapsed >= self.min_seconds_between_replies_per_chat

    def _send_message(self, message: str) -> None:
        assert self._driver is not None

        composer = WebDriverWait(self._driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, "//footer//div[@contenteditable='true']")
            )
        )

        lines = message.split("\\n")
        for index, line in enumerate(lines):
            composer.send_keys(line)
            if index < len(lines) - 1:
                composer.send_keys(Keys.SHIFT, Keys.ENTER)

        composer.send_keys(Keys.ENTER)
