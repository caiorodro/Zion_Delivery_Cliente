import flet as ft

from frontend.cfg.config import AppConfig
from frontend.models.sacola import PagamentoPedido
from frontend.style.zControls import (
    zButton, zTextField, zLabel, zTitle, zCard, zDivider, zSnackBar
)
from frontend.utils.currency_formatter import format_currency


class Pagamento:
    """View 4 – Forma de pagamento."""

    FORMAS = ["CARTÃO", "DINHEIRO", "PIX"]

    def __init__(self, page: ft.Page, sacola):
        self.page = page
        self.sacola = sacola
        self.panel = None
        self._init_controls()
        self._build_layout()

    # ─── Inicialização ──────────────────────────────────────────

    def _init_controls(self):
        self.rg_pagamento = ft.RadioGroup(
            content=ft.Column(
                controls=[
                    ft.Radio(
                        value="CARTÃO",
                        label="💳  Cartão",
                        label_style=ft.TextStyle(color=AppConfig.FONT_COLOR, size=16)
                    ),
                    ft.Radio(
                        value="DINHEIRO",
                        label="💵  Dinheiro",
                        label_style=ft.TextStyle(color=AppConfig.FONT_COLOR, size=16)
                    ),
                    ft.Radio(
                        value="PIX",
                        label="📱  Pix",
                        label_style=ft.TextStyle(color=AppConfig.FONT_COLOR, size=16)
                    ),
                ]
            ),
            on_change=self._on_pagamento_change
        )

        self.row_troco = ft.Row(
            controls=[
                zLabel("Precisa de troco?"),
                ft.Checkbox(
                    label="Sim",
                    value=False,
                    check_color="#ffffff",
                    active_color=AppConfig.BTN_PRIMARY,
                    label_style=ft.TextStyle(color=AppConfig.FONT_COLOR),
                    on_change=self._on_troco_check
                ),
            ],
            visible=False
        )

        self.chk_troco = self.row_troco.controls[1]

        self.txt_troco = zTextField(
            label="Troco para (R$) *",
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="Ex: 50.00",
            visible=False
        )

        self.btn_voltar = zButton(
            text="← Voltar",
            on_click=lambda e: self.page.go("/cliente"),
            width=140
        )
        self.btn_proximo = zButton(
            text="Revisar pedido →",
            on_click=self._validar_e_avancar,
            width=200
        )

    def _build_layout(self):
        bg = AppConfig.BG_COLOR

        self.panel = ft.View(
            route="/pagamento",
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
                            spacing=16,
                            controls=[
                                zTitle("💳  Forma de Pagamento"),
                                zDivider(),
                                zLabel("Selecione como deseja pagar:"),
                                self.rg_pagamento,
                                self.row_troco,
                                ft.Row([self.txt_troco], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Row(
                                    [self.btn_voltar, self.btn_proximo],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                            ],
                        ),
                    ),
                )
            ],
        )

    # ─── Eventos ────────────────────────────────────────────────

    def _on_pagamento_change(self, e):
        is_dinheiro = self.rg_pagamento.value == "DINHEIRO"
        self.row_troco.visible = is_dinheiro
        if not is_dinheiro:
            self.chk_troco.value = False
            self.txt_troco.visible = False
        try:
            self.row_troco.update()
            self.txt_troco.update()
        except Exception:
            pass

    def _on_troco_check(self, e):
        self.txt_troco.visible = self.chk_troco.value
        try:
            self.txt_troco.update()
        except Exception:
            pass

    def _validar_e_avancar(self, e):
        forma = self.rg_pagamento.value
        if not forma:
            self._show_snack("Selecione a forma de pagamento.", error=True)
            return

        troco_para = 0.0
        if forma == "DINHEIRO" and self.chk_troco.value:
            try:
                troco_para = float((self.txt_troco.value or "0").replace(",", "."))
                if troco_para <= 0:
                    self._show_snack("Informe um valor válido para o troco.", error=True)
                    self.txt_troco.focus()
                    return
            except ValueError:
                self._show_snack("Valor de troco inválido.", error=True)
                self.txt_troco.focus()
                return

        self.sacola.PAGAMENTO = PagamentoPedido(
            FORMA_PAGAMENTO=forma,
            TROCO_PARA=troco_para,
        )

        self.page.go("/confirmacao")

    def carregar_dados(self):
        """Preenche campos com dados já salvos na sacola."""
        pg = self.sacola.PAGAMENTO
        self.rg_pagamento.value = pg.FORMA_PAGAMENTO
        is_dinheiro = pg.FORMA_PAGAMENTO == "DINHEIRO"
        self.row_troco.visible = is_dinheiro
        if pg.TROCO_PARA > 0:
            self.chk_troco.value = True
            self.txt_troco.visible = True
            self.txt_troco.value = str(pg.TROCO_PARA)
        try:
            self.rg_pagamento.update()
            self.row_troco.update()
            self.txt_troco.update()
        except Exception:
            pass

    # ─── Helpers ────────────────────────────────────────────────

    def _show_snack(self, text: str, error: bool = False):
        from frontend.style.zControls import zSnackBar
        self.page.open(zSnackBar(text, error=error))
