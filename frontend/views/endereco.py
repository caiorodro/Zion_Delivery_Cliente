import threading
import time
import json
import math
import os

import flet as ft

from frontend.base.server import ZionAPI
from frontend.cfg.config import AppConfig
from frontend.models.dadosEndereco import DadosEndereco
from frontend.style.zControls import (
    zButton, zTextField, zDropdown, zLabel, zTitle, zCard, zDivider, zSnackBar
)


class Endereco:
    """View 1 – Endereço de entrega do cliente."""

    STORAGE_KEY_ENDERECO = "zion_endereco_v1"

    def __init__(self, page: ft.Page, sacola):
        self.page = page
        self.sacola = sacola
        self.panel = None
        self._ufs: list = []
        self._cidades: list = []
        self._enderecos: list = []
        self._dados_endereco_salvo: dict = {}
        self._latitude_cliente = None
        self._longitude_cliente = None
        self._search_timer = None
        self._init_controls()
        self._build_layout()
        self._carregar_endereco_salvo_local()
        self._load_ufs()

    # ─── Inicialização ──────────────────────────────────────────

    def _init_controls(self):
        self.txt_rua = zTextField(
            label="Rua / Logradouro *",
            width=360,
            hint_text="Digite o nome da rua"
        )
        self.txt_numero = zTextField(label="Número *", width=100)
        self.txt_complemento = zTextField(label="Complemento", width=200)
        self.txt_cep = zTextField(
            label="CEP",
            width=130,
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_text="00000-000",
            on_submit=self._buscar_por_cep
        )
        self.txt_bairro = zTextField(label="Bairro *", width=220)
        self.txt_obs = zTextField(
            label="Observações para o entregador",
            width=470,
            hint_text="Ponto de referência, portão, etc."
        )

        self.cb_uf = zDropdown(
            label="Estado (UF) *",
            width=120,
            on_change=self._on_uf_change
        )
        self.txt_pesq_cidade = zTextField(
            label="Filtrar cidade...",
            width=200,
            hint_text="Digite para filtrar",
            on_change=self._on_pesq_cidade_change
        )
        self.cb_cidade = zDropdown(
            label="Cidade *",
            width=260,
            on_change=self._on_cidade_change
        )

        self.txt_pesq_rua = zTextField(
            label="Pesquisar rua / bairro / CEP",
            width=470,
            hint_text="Mínimo 2 caracteres",
            on_change=self._on_pesq_rua_change
        )

        self.lst_enderecos = ft.ListView(
            controls=[],
            height=160,
            spacing=2,
            visible=False,
        )

        self.progress = ft.ProgressRing(
            width=24, height=24, stroke_width=3,
            color=AppConfig.BTN_PRIMARY,
            visible=False
        )

        self.btn_proximo = zButton(
            text="Próximo →",
            on_click=self._validar_e_avancar,
            width=180
        )

    def _build_layout(self):
        bg = AppConfig.BG_COLOR

        self.panel = ft.View(
            route="/endereco",
            bgcolor=bg,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.top_center,
                    content=ft.Container(
                        width=760,
                        padding=ft.padding.symmetric(horizontal=18, vertical=14),
                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            spacing=16,
                            horizontal_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Row(
                                    [zTitle("🏠  Endereço de Entrega"),
                                     self.progress],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                zDivider(),

                                # UF, filtro de cidade e combo cidade
                                zLabel("Selecione o estado e cidade para localizar o endereço:"),
                                ft.Row([self.cb_uf, self.txt_pesq_cidade, self.cb_cidade], wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START),

                                # Pesquisa de rua
                                zLabel("Pesquisar endereço:"),
                                ft.Row([self.txt_pesq_rua], wrap=True, alignment=ft.MainAxisAlignment.START),
                                self.lst_enderecos,

                                zDivider(),
                                zLabel("Preencha os dados abaixo:"),

                                # Rua + número
                                ft.Row([self.txt_rua, self.txt_numero], wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START),
                                # Complemento + CEP
                                ft.Row([self.txt_complemento, self.txt_cep], wrap=True, spacing=10, alignment=ft.MainAxisAlignment.START),
                                # Bairro
                                ft.Row([self.txt_bairro], wrap=True, alignment=ft.MainAxisAlignment.START),
                                # Observações
                                ft.Row([self.txt_obs], wrap=True, alignment=ft.MainAxisAlignment.START),

                                ft.Row(
                                    [self.btn_proximo],
                                    alignment=ft.MainAxisAlignment.END
                                ),
                            ],
                        ),
                    ),
                )
            ],
        )

    # ─── Carregamento de UFs ────────────────────────────────────

    def _load_ufs(self):
        def _task():
            self._show_progress(True)
            api = ZionAPI()
            ufs = api.get_ufs()
            self._ufs = ufs
            self.cb_uf.options = [
                ft.dropdown.Option(key=uf, text=uf) for uf in ufs
            ]
            try:
                self.cb_uf.update()
            except Exception:
                pass

            uf_salva = (self._dados_endereco_salvo.get("UF") or "").strip()
            cidade_salva = (self._dados_endereco_salvo.get("CIDADE") or "").strip()
            if uf_salva and uf_salva in self._ufs:
                self.cb_uf.value = uf_salva
                self._carregar_cidades_da_uf(uf_salva, cidade_preselecionada=cidade_salva)

            self._show_progress(False)

        threading.Thread(target=_task, daemon=True).start()

    def _carregar_cidades_da_uf(self, uf: str, cidade_preselecionada: str = ""):
        api = ZionAPI()
        cidades = api.get_cidades(uf)
        self._cidades = cidades
        self.cb_cidade.options = [
            ft.dropdown.Option(key=c, text=c) for c in cidades
        ]

        if cidade_preselecionada and cidade_preselecionada in cidades:
            self.cb_cidade.value = cidade_preselecionada
            self.txt_pesq_cidade.value = cidade_preselecionada
        else:
            self.cb_cidade.value = None

        try:
            self.cb_uf.update()
            self.txt_pesq_cidade.update()
            self.cb_cidade.update()
        except Exception:
            pass

    def _on_uf_change(self, e):
        uf = self.cb_uf.value
        if not uf:
            return

        def _task():
            self._show_progress(True)
            self.txt_pesq_cidade.value = ""
            self._carregar_cidades_da_uf(uf)
            try:
                self.txt_pesq_cidade.update()
            except Exception:
                pass
            self._show_progress(False)

        threading.Thread(target=_task, daemon=True).start()

    def _on_cidade_change(self, e):
        self.txt_pesq_rua.value = ""
        self.lst_enderecos.controls.clear()
        self.lst_enderecos.visible = False
        try:
            self.lst_enderecos.update()
        except Exception:
            pass

    def _on_pesq_cidade_change(self, e):
        """Filtra o combo de cidades conforme o usuário digita."""
        termo = (self.txt_pesq_cidade.value or "").strip().lower()

        if not termo:
            filtradas = self._cidades
        else:
            filtradas = [c for c in self._cidades if termo in c.lower()]

        self.cb_cidade.options = [
            ft.dropdown.Option(key=c, text=c) for c in filtradas
        ]

        if len(filtradas) > 0:
            self.cb_cidade.value = filtradas[0]

        try:
            self.cb_cidade.update()
        except Exception:
            pass

    # ─── Pesquisa de rua ────────────────────────────────────────

    def _on_pesq_rua_change(self, e):
        termo = (self.txt_pesq_rua.value or "").strip()
        if len(termo) < 2:
            self.lst_enderecos.controls.clear()
            self.lst_enderecos.visible = False
            try:
                self.lst_enderecos.update()
            except Exception:
                pass
            return

        # Debounce: aguarda 1000ms antes de pesquisar
        if self._search_timer:
            self._search_timer.cancel()

        self._search_timer = threading.Timer(1, self._executar_pesquisa, args=[termo])
        self._search_timer.start()

    def onlyNumbers(self, s: str) -> str:
        return ''.join(filter(str.isdigit, s))  

    def _executar_pesquisa(self, termo: str):

        api = ZionAPI()

        if len(self.onlyNumbers(termo)) == 8:
            self._show_progress(True)
            enderecos = api.buscar_por_cep(termo)
            self._enderecos = enderecos
            self._show_progress(False)

            if enderecos:
                self._selecionar_endereco(enderecos[0])
                return

        uf = self.cb_uf.value
        cidade = self.cb_cidade.value
        if not uf or not cidade:
            return

        self._show_progress(True)
        
        enderecos = api.pesquisar_endereco(uf, cidade, termo)
        self._enderecos = enderecos

        self.lst_enderecos.controls.clear()

        for end in enderecos[:40]:
            label = f"{end['LOGRADOURO']} – {end['BAIRRO']} – CEP: {end['CEP']}"
            self.lst_enderecos.controls.append(
                ft.ListTile(
                    title=ft.Text(label, size=13, color="#333333"),
                    dense=True,
                    on_click=lambda e, en=end: self._selecionar_endereco(en),
                )
            )

        self.lst_enderecos.visible = bool(enderecos)
        try:
            self.lst_enderecos.update()
        except Exception:
            pass
        self._show_progress(False)

    def _buscar_por_cep(self, e):
        cep = (self.txt_cep.value or "").strip()
        if len(cep) < 8:
            return

        def _task():
            self._show_progress(True)
            api = ZionAPI()
            result = api.buscar_por_cep(cep)
            if result:
                self._selecionar_endereco(result[0])
            self._show_progress(False)

        threading.Thread(target=_task, daemon=True).start()

    def _selecionar_endereco(self, end: dict):
        self.txt_rua.value = end.get("LOGRADOURO", "")
        self.txt_bairro.value = end.get("BAIRRO", "")
        self.txt_cep.value = end.get("CEP", "")
        self._latitude_cliente = self._parse_float(end.get("LATITUDE"))
        self._longitude_cliente = self._parse_float(end.get("LONGITUDE"))
        self.lst_enderecos.visible = False
        self.txt_pesq_rua.value = end.get("LOGRADOURO", "")

        # Sincroniza UF e cidade se vieram da pesquisa por CEP
        uf = end.get("UF", "")
        cidade = end.get("CIDADE", "")
        if uf and self.cb_uf.value != uf:
            self.cb_uf.value = uf
        if cidade and self.cb_cidade.value != cidade:
            self.cb_cidade.value = cidade
            self.txt_pesq_cidade.value = cidade

        try:
            self.txt_rua.update()
            self.txt_bairro.update()
            self.txt_cep.update()
            self.txt_pesq_rua.update()
            self.txt_pesq_cidade.update()
            self.lst_enderecos.update()
            self.cb_uf.update()
            self.cb_cidade.update()
        except Exception as ex:
            print(f"Erro ao atualizar controles: {ex}")

        self.txt_numero.focus()

    # ─── Validação e avanço ─────────────────────────────────────

    def _validar_e_avancar(self, e):
        campos = [
            (self.txt_rua, "Rua / Logradouro"),
            (self.txt_numero, "Número"),
            (self.txt_bairro, "Bairro"),
            (self.txt_cep, "CEP"),
        ]

        uf = self.cb_uf.value
        cidade = self.cb_cidade.value

        if not uf or not cidade:
            self._show_snack("Selecione o Estado e Cidade.", error=True)
            return

        for ctrl, nome in campos:
            if not ctrl.value or not ctrl.value.strip():
                self._show_snack(f"Campo obrigatório: {nome}", error=True)
                ctrl.focus()
                return

        # Atualiza a sacola
        self.sacola.DADOS_ENDERECO = DadosEndereco(
            RUA=self.txt_rua.value.strip(),
            NUMERO=self.txt_numero.value.strip(),
            COMPLEMENTO=(self.txt_complemento.value or "").strip(),
            CEP=self.txt_cep.value.strip(),
            BAIRRO=self.txt_bairro.value.strip(),
            CIDADE=cidade,
            UF=uf,
            OBS_ENTREGADOR=(self.txt_obs.value or "").strip(),
        )

        taxa, distancia = self._calcular_taxa_entrega()
        self.sacola.TAXA_ENTREGA = taxa

        if distancia is not None:
            self._show_snack(f"Taxa de entrega atualizada (distância: {distancia:.2f} km).")
        else:
            self._show_snack("Não foi possível calcular distância. Aplicada taxa fixa.")

        self._salvar_endereco_local(self.sacola.DADOS_ENDERECO)

        self.page.go("/cardapio")

    # ─── Helpers ────────────────────────────────────────────────

    def _show_progress(self, visible: bool):
        self.progress.visible = visible
        try:
            self.progress.update()
        except Exception:
            pass

    def _carregar_endereco_salvo_local(self):
        try:
            dados = self.page.client_storage.get(self.STORAGE_KEY_ENDERECO)
        except Exception:
            dados = None

        if not isinstance(dados, dict):
            return

        self._dados_endereco_salvo = dados
        self._latitude_cliente = self._parse_float(dados.get("LATITUDE"))
        self._longitude_cliente = self._parse_float(dados.get("LONGITUDE"))

        self.txt_rua.value = (dados.get("RUA") or "").strip()
        self.txt_numero.value = (dados.get("NUMERO") or "").strip()
        self.txt_complemento.value = (dados.get("COMPLEMENTO") or "").strip()
        self.txt_cep.value = (dados.get("CEP") or "").strip()
        self.txt_bairro.value = (dados.get("BAIRRO") or "").strip()
        self.txt_obs.value = (dados.get("OBS_ENTREGADOR") or "").strip()

        uf_salva = (dados.get("UF") or "").strip()
        cidade_salva = (dados.get("CIDADE") or "").strip()
        if uf_salva:
            self.cb_uf.value = uf_salva
        if cidade_salva:
            self.cb_cidade.value = cidade_salva
            self.txt_pesq_cidade.value = cidade_salva

        try:
            self.txt_rua.update()
            self.txt_numero.update()
            self.txt_complemento.update()
            self.txt_cep.update()
            self.txt_bairro.update()
            self.txt_obs.update()
            self.cb_uf.update()
            self.cb_cidade.update()
            self.txt_pesq_cidade.update()
        except Exception:
            pass

    def _salvar_endereco_local(self, dados: DadosEndereco):
        payload = {
            "RUA": dados.RUA,
            "NUMERO": dados.NUMERO,
            "COMPLEMENTO": dados.COMPLEMENTO,
            "CEP": dados.CEP,
            "BAIRRO": dados.BAIRRO,
            "CIDADE": dados.CIDADE,
            "UF": dados.UF,
            "OBS_ENTREGADOR": dados.OBS_ENTREGADOR,
            "LATITUDE": self._latitude_cliente,
            "LONGITUDE": self._longitude_cliente,
        }
        try:
            self.page.client_storage.set(self.STORAGE_KEY_ENDERECO, payload)
            self._dados_endereco_salvo = payload
        except Exception:
            pass

    def _parse_float(self, value):
        if value is None:
            return None
        try:
            return float(str(value).replace(",", "."))
        except (ValueError, TypeError):
            return None

    def _carregar_config_loja(self) -> dict:
        default_cfg = {
            "latitude": None,
            "longitude": None,
            "taxa_entrega_fixa": AppConfig.TAXA_ENTREGA_FALLBACK,
        }

        path_cfg = AppConfig.LOJA_CONFIG
        os.makedirs(os.path.dirname(path_cfg), exist_ok=True)

        if not os.path.exists(path_cfg):
            with open(path_cfg, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, ensure_ascii=False, indent=2)
            return default_cfg

        try:
            with open(path_cfg, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not isinstance(cfg, dict):
                return default_cfg
            return {
                "latitude": self._parse_float(cfg.get("latitude")),
                "longitude": self._parse_float(cfg.get("longitude")),
                "taxa_entrega_fixa": self._parse_float(cfg.get("taxa_entrega_fixa"))
                or AppConfig.TAXA_ENTREGA_FALLBACK,
            }
        except Exception:
            return default_cfg

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def _calcular_taxa_entrega(self) -> tuple:
        cfg_loja = self._carregar_config_loja()
        taxa_fixa = self._parse_float(cfg_loja.get("taxa_entrega_fixa")) or AppConfig.TAXA_ENTREGA_FALLBACK

        lat_loja = self._parse_float(cfg_loja.get("latitude"))
        lon_loja = self._parse_float(cfg_loja.get("longitude"))
        lat_cli = self._parse_float(self._latitude_cliente)
        lon_cli = self._parse_float(self._longitude_cliente)

        if None in (lat_loja, lon_loja, lat_cli, lon_cli):
            return taxa_fixa, None

        try:
            distancia_km = self._haversine_km(lat_loja, lon_loja, lat_cli, lon_cli)
        except Exception:
            return taxa_fixa, None

        try:
            api = ZionAPI()
            faixa = api.get_faixa_frete(distancia_km)
            if isinstance(faixa, dict) and faixa:
                valor = self._parse_float(faixa.get("VALOR_FRETE"))
                if valor is not None:
                    return valor, distancia_km
        except Exception:
            pass

        return taxa_fixa, distancia_km

    def _show_snack(self, text: str, error: bool = False):
        self.page.open(zSnackBar(text, error=error))
