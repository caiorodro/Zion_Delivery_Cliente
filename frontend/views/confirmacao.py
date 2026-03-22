import threading
import time

import flet as ft

from frontend.base.server import ZionAPI
from frontend.cfg.config import AppConfig
from frontend.style.zControls import (
    zButton, zLabel, zTitle, zCard, zDivider, zSnackBar
)
from frontend.utils.currency_formatter import format_currency


STATUS_LABELS = {
    0: "⏳ Aguardando confirmação da loja...",
    1: "✅ Pedido aceito! Preparando...",
    2: "👨‍🍳 Em preparo...",
    3: "🛵 Saiu para entrega!",
    4: "🎉 Pedido entregue!",
    99: "❌ Pedido cancelado.",
}


class Confirmacao:
    """View 5 – Conferência e envio do pedido."""

    def __init__(self, page: ft.Page, sacola):
        self.page = page
        self.sacola = sacola
        self.panel = None
        self._numero_pedido = None
        self._polling_active = False
        self._init_controls()
        self._build_layout()

    # ─── Inicialização ──────────────────────────────────────────

    def _init_controls(self):
        self.col_itens = ft.Column(controls=[], spacing=4)

        self.lbl_total_prods = zLabel("", size=14)
        self.lbl_taxa = zLabel("", size=14)
        self.lbl_total = zLabel("", size=16, bold=True)
        self.lbl_pagamento = zLabel("", size=14)
        self.lbl_troco = zLabel("", size=14, color="#555555")
        self.lbl_endereco = zLabel("", size=13, color="#555555")
        self.lbl_cliente = zLabel("", size=13, color="#555555")

        self.progress_envio = ft.Column(
            visible=False,
            spacing=8,
            controls=[
                ft.ProgressBar(color=AppConfig.BTN_PRIMARY, bgcolor=ft.colors.GREY_200),
                zLabel("Enviando pedido...", size=13, color="#555555"),
            ]
        )

        self.col_status = ft.Column(
            visible=False,
            spacing=10,
            controls=[
                zDivider(),
                zLabel("Status do pedido:", size=15, bold=True),
                ft.ProgressRing(
                    width=32, height=32, stroke_width=3,
                    color=AppConfig.BTN_PRIMARY,
                ),
            ]
        )
        self._ring_status = self.col_status.controls[2]
        self.lbl_status = zLabel("", size=15, bold=True)

        self.btn_voltar = zButton(
            text="← Voltar",
            on_click=lambda e: self.page.go("/pagamento"),
            width=140
        )
        self.btn_confirmar = zButton(
            text="✔  Confirmar Pedido",
            on_click=self._confirmar_pedido,
            width=220,
            icon=ft.icons.CHECK_CIRCLE_OUTLINE
        )
        self.btn_inicio = zButton(
            text="🏠  Voltar para o início",
            on_click=lambda e: self.page.go("/cardapio"),
            width=220,
            visible=False,
        )

    def _build_layout(self):
        bg = AppConfig.BG_COLOR

        self.panel = ft.View(
            route="/confirmacao",
            bgcolor=bg,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.top_center,
                    content=ft.Container(
                        width=1024,
                        padding=ft.padding.symmetric(horizontal=20, vertical=16),
                        content=ft.Column(
                            spacing=14,
                            controls=[
                                zTitle("📋  Conferência do Pedido"),
                                zDivider(),

                                zLabel("Itens do pedido:", bold=True),
                                self.col_itens,
                                zDivider(),

                                ft.Row([zLabel("Subtotal:", bold=True), self.lbl_total_prods],
                                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([zLabel("Taxa de entrega:", bold=True), self.lbl_taxa],
                                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([zLabel("TOTAL:", bold=True, size=18), self.lbl_total],
                                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                zDivider(),

                                zLabel("Pagamento:", bold=True),
                                self.lbl_pagamento,
                                self.lbl_troco,
                                zDivider(),

                                zLabel("Entregar em:", bold=True),
                                self.lbl_cliente,
                                self.lbl_endereco,
                                zDivider(),

                                self.progress_envio,
                                self.col_status,
                                self.lbl_status,

                                ft.Row(
                                    [self.btn_voltar, self.btn_confirmar],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                ft.Row(
                                    [self.btn_inicio],
                                    alignment=ft.MainAxisAlignment.CENTER
                                ),
                            ],
                        ),
                    ),
                )
            ],
        )

    # ─── Carregamento da tela ───────────────────────────────────

    def carregar_dados(self):
        s = self.sacola

        # Itens
        self.col_itens.controls.clear()
        for it in s.ITEMS:
            self.col_itens.controls.append(
                ft.Row(
                    [
                        ft.Text(f"{it.QTDE}x {it.DESCRICAO_PRODUTO}",
                                size=13, color="#333333", expand=True),
                        ft.Text(format_currency(it.TOTAL_ITEM),
                                size=13, color=AppConfig.FONT_COLOR),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        # Totais
        self.lbl_total_prods.value = format_currency(s.total_produtos)
        self.lbl_taxa.value = format_currency(s.TAXA_ENTREGA)
        self.lbl_total.value = format_currency(s.total_pedido)

        # Pagamento
        forma = s.PAGAMENTO.FORMA_PAGAMENTO
        self.lbl_pagamento.value = f"💳  {forma}"
        if forma == "DINHEIRO" and s.PAGAMENTO.TROCO_PARA > 0:
            self.lbl_troco.value = f"Troco para: {format_currency(s.PAGAMENTO.TROCO_PARA)}"
            self.lbl_troco.visible = True
        else:
            self.lbl_troco.visible = False

        # Cliente e endereço
        c = s.DADOS_CLIENTE
        en = s.DADOS_ENDERECO
        self.lbl_cliente.value = (
            f"{c.NOME_CLIENTE}"
            + (f"  |  CPF: {c.CPF}" if c.CPF_NO_CUPOM and c.CPF else "")
            + (f"  |  Tel: {c.TELEFONE}" if c.TELEFONE else "")
        )
        self.lbl_endereco.value = (
            f"{en.RUA}, {en.NUMERO}"
            + (f" – {en.COMPLEMENTO}" if en.COMPLEMENTO else "")
            + f" | {en.BAIRRO} | {en.CIDADE}/{en.UF} | CEP {en.CEP}"
            + (f"\nRef: {en.OBS_ENTREGADOR}" if en.OBS_ENTREGADOR else "")
        )

        # Resetar estado de envio
        self.progress_envio.visible = False
        self.col_status.visible = False
        self.lbl_status.value = ""
        self.btn_confirmar.visible = True
        self.btn_voltar.visible = True
        self.btn_inicio.visible = False

        try:
            self.col_itens.update()
            self.lbl_total_prods.update()
            self.lbl_taxa.update()
            self.lbl_total.update()
            self.lbl_pagamento.update()
            self.lbl_troco.update()
            self.lbl_cliente.update()
            self.lbl_endereco.update()
            self.progress_envio.update()
            self.col_status.update()
            self.lbl_status.update()
            self.btn_confirmar.update()
            self.btn_voltar.update()
        except Exception:
            pass

    # ─── Confirmação e envio ────────────────────────────────────

    def _confirmar_pedido(self, e):
        if not self.sacola.ITEMS:
            self._show_snack("A sacola está vazia!", error=True)
            return

        self.btn_confirmar.visible = False
        self.btn_voltar.visible = False
        self.progress_envio.visible = True
        try:
            self.btn_confirmar.update()
            self.btn_voltar.update()
            self.progress_envio.update()
        except Exception:
            pass

        threading.Thread(target=self._enviar_pedido, daemon=True).start()

    def _enviar_pedido(self):
        api = ZionAPI()

        # Atualiza texto de progresso
        self._set_progress_text("Conectando ao servidor...")

        try:
            resultado = api.criar_pedido(self.sacola.to_dict())
        except Exception as ex:
            self._mostrar_erro(f"Erro ao enviar pedido: {ex}")
            return

        if resultado is None:
            self._mostrar_erro("Não foi possível enviar o pedido. Verifique sua conexão.")
            return

        self._numero_pedido = resultado.get("NUMERO_PEDIDO")
        self._set_progress_text(f"Pedido #{self._numero_pedido} enviado! Aguardando confirmação...")

        self.progress_envio.visible = False
        self.col_status.visible = True
        self._ring_status.visible = True
        self.lbl_status.value = STATUS_LABELS.get(0, "Aguardando...")
        try:
            self.progress_envio.update()
            self.col_status.update()
            self.lbl_status.update()
        except Exception:
            pass

        self._iniciar_polling()

    def _iniciar_polling(self):
        self._polling_active = True
        start = time.time()
        api = ZionAPI()

        while self._polling_active:
            elapsed = time.time() - start
            if elapsed > AppConfig.POLLING_TIMEOUT:
                self._set_status_label("⚠ O servidor demorou para responder. Verifique com a loja.")
                self._ring_status.visible = False
                try:
                    self._ring_status.update()
                except Exception:
                    pass
                break

            time.sleep(AppConfig.POLLING_INTERVAL)

            try:
                status_data = api.get_status_pedido(self._numero_pedido)
            except Exception:
                continue

            if status_data is None:
                continue

            status_code = status_data.get("STATUS_PEDIDO", 0)
            descricao = STATUS_LABELS.get(status_code, status_data.get("DESCRICAO_STATUS", ""))
            self._set_status_label(descricao)

            if status_code in (1, 2, 3, 4, 99):
                self._ring_status.visible = False
                try:
                    self._ring_status.update()
                except Exception:
                    pass

            if status_code >= 1:
                self.btn_inicio.visible = True
                try:
                    self.btn_inicio.update()
                except Exception:
                    pass

            if status_code in (4, 99):
                self._polling_active = False
                break

    def _set_progress_text(self, text: str):
        if len(self.progress_envio.controls) > 1:
            self.progress_envio.controls[1].value = text
            try:
                self.progress_envio.controls[1].update()
            except Exception:
                pass

    def _set_status_label(self, text: str):
        self.lbl_status.value = text
        try:
            self.lbl_status.update()
        except Exception:
            pass

    def _mostrar_erro(self, msg: str):
        self.progress_envio.visible = False
        self.btn_confirmar.visible = True
        self.btn_voltar.visible = True
        try:
            self.progress_envio.update()
            self.btn_confirmar.update()
            self.btn_voltar.update()
        except Exception:
            pass
        self._show_snack(msg, error=True)

    # ─── Helpers ────────────────────────────────────────────────

    def _show_snack(self, text: str, error: bool = False):
        from frontend.style.zControls import zSnackBar
        self.page.open(zSnackBar(text, error=error))
