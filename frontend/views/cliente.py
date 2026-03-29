import flet as ft

from frontend.cfg.config import AppConfig
from frontend.models.dadosCliente import DadosCliente
from frontend.style.zControls import (
    zButton, zTextField, zLabel, zTitle, zDivider, zSnackBar
)


class Cliente:
    """View 3 – Nome do cliente e CPF no cupom fiscal."""

    STORAGE_KEY_CLIENTE = "zion_cliente_v1"

    def __init__(self, page: ft.Page, sacola):
        self.page = page
        self.sacola = sacola
        self.panel = None
        self._dados_cliente_salvo: dict = {}
        self._init_controls()
        self._build_layout()
        self._carregar_cliente_salvo_local()

    # ─── Inicialização ──────────────────────────────────────────

    def _init_controls(self):
        self.txt_nome = zTextField(
            label="Seu nome *",
            width=320,
            autofocus=True,
            hint_text="Como você gostaria de ser chamado?"
        )

        self.txt_telefone = zTextField(
            label="Telefone / WhatsApp",
            width=200,
            keyboard_type=ft.KeyboardType.PHONE,
            hint_text="(00) 00000-0000"
        )

        self.txt_obs = zTextField(
            label="Observações do pedido",
            width=520,
            hint_text="Ex.: retirar sem cebola, ponto de referência, etc."
        )
        
        self.chk_cpf = ft.Checkbox(
            label="Quero CPF no cupom fiscal",
            value=False,
            check_color="#ffffff",
            active_color=AppConfig.BTN_PRIMARY,
            label_style=ft.TextStyle(color=AppConfig.FONT_COLOR),
            on_change=self._on_cpf_check
        )

        self.txt_cpf = zTextField(
            label="CPF",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="000.000.000-00",
            visible=False,
            max_length=14
        )

        self.btn_voltar = zButton(
            text="← Voltar",
            on_click=lambda e: self.page.go("/cardapio"),
            width=140
        )
        self.btn_proximo = zButton(
            text="Próximo →",
            on_click=self._validar_e_avancar,
            width=180
        )

    def _build_layout(self):
        bg = AppConfig.BG_COLOR

        self.panel = ft.View(
            route="/cliente",
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
                                zTitle("👤  Seus Dados"),
                                zDivider(),
                                zLabel("Informe seus dados para que possamos identificar o pedido:"),
                                ft.Row([self.txt_nome], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Row([self.txt_telefone], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Row([self.txt_obs], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Row([self.chk_cpf], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
                                ft.Row([self.txt_cpf], wrap=True, alignment=ft.MainAxisAlignment.CENTER),
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

    def _on_cpf_check(self, e):
        self.txt_cpf.visible = self.chk_cpf.value
        try:
            self.txt_cpf.update()
        except Exception:
            pass

    def _validar_e_avancar(self, e):
        nome = (self.txt_nome.value or "").strip()
        if not nome:
            self._show_snack("Informe seu nome.", error=True)
            self.txt_nome.focus()
            return

        cpf = ""
        if self.chk_cpf.value:
            cpf = (self.txt_cpf.value or "").strip()
            if len(cpf.replace(".", "").replace("-", "")) != 11:
                self._show_snack("CPF inválido. Informe 11 dígitos.", error=True)
                self.txt_cpf.focus()
                return

        self.sacola.DADOS_CLIENTE = DadosCliente(
            NOME_CLIENTE=nome,
            CPF=cpf,
            TELEFONE=(self.txt_telefone.value or "").strip(),
            CPF_NO_CUPOM=self.chk_cpf.value,
        )
        self.sacola.OBS_PEDIDO = (self.txt_obs.value or "").strip()
        self._salvar_cliente_local(self.sacola.DADOS_CLIENTE, self.sacola.OBS_PEDIDO)

        self.page.go("/pagamento")

    def carregar_dados(self):
        """Preenche campos com dados já salvos na sacola."""
        c = self.sacola.DADOS_CLIENTE
        nome = (c.NOME_CLIENTE or "").strip() or str(self._dados_cliente_salvo.get("NOME_CLIENTE") or "").strip()
        telefone = (c.TELEFONE or "").strip() or str(self._dados_cliente_salvo.get("TELEFONE") or "").strip()
        obs_pedido = (self.sacola.OBS_PEDIDO or "").strip() or str(self._dados_cliente_salvo.get("OBS_PEDIDO") or "").strip()

        cpf_no_cupom = bool(c.CPF_NO_CUPOM)
        if not cpf_no_cupom:
            cpf_no_cupom = bool(self._dados_cliente_salvo.get("CPF_NO_CUPOM"))

        cpf = (c.CPF or "").strip() or str(self._dados_cliente_salvo.get("CPF") or "").strip()

        self.txt_nome.value = nome
        self.txt_telefone.value = telefone
        self.txt_obs.value = obs_pedido
        self.chk_cpf.value = cpf_no_cupom
        self.txt_cpf.value = cpf
        self.txt_cpf.visible = cpf_no_cupom
        try:
            self.txt_nome.update()
            self.txt_telefone.update()
            self.txt_obs.update()
            self.chk_cpf.update()
            self.txt_cpf.update()
        except Exception:
            pass

    def _carregar_cliente_salvo_local(self):
        try:
            dados = self.page.client_storage.get(self.STORAGE_KEY_CLIENTE)
        except Exception:
            dados = None

        if not isinstance(dados, dict):
            return

        self._dados_cliente_salvo = dados

    def _salvar_cliente_local(self, dados_cliente: DadosCliente, obs_pedido: str):
        payload = {
            "NOME_CLIENTE": dados_cliente.NOME_CLIENTE,
            "CPF": dados_cliente.CPF,
            "TELEFONE": dados_cliente.TELEFONE,
            "CPF_NO_CUPOM": bool(dados_cliente.CPF_NO_CUPOM),
            "OBS_PEDIDO": (obs_pedido or "").strip(),
        }
        try:
            self.page.client_storage.set(self.STORAGE_KEY_CLIENTE, payload)
            self._dados_cliente_salvo = payload
        except Exception:
            pass

    # ─── Helpers ────────────────────────────────────────────────

    def _show_snack(self, text: str, error: bool = False):
        from frontend.style.zControls import zSnackBar
        self.page.open(zSnackBar(text, error=error))
