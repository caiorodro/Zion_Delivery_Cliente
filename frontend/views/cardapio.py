import flet as ft

from frontend.base.cache import CacheManager
from frontend.cfg.config import AppConfig
from frontend.models.itemPedido import ItemPedido
from frontend.style.zControls import (
    zButton, zTextField, zDropdown, zLabel, zTitle, zCard, zDivider, zSnackBar
)
from frontend.utils.currency_formatter import format_currency


class Cardapio:
    """View 2 – Filtro e escolha de produtos."""

    def __init__(self, page: ft.Page, sacola):
        self.page = page
        self.sacola = sacola
        self.panel = None
        self._qtde_map: dict = {}   # ID_PRODUTO -> TextField
        self._produtos_filtrados = []
        self._indice_carregado = 0
        self._tam_pagina = 30
        self._carregando_pagina = False
        self._init_controls()
        self._build_layout()
        self._carregar_familias()
        self._carregar_cardapio()

    # ─── Inicialização ──────────────────────────────────────────

    def _init_controls(self):
        self.txt_pesq = zTextField(
            label="Pesquisar produto...",
            width=260,
            autofocus=True,
            on_submit=lambda e: self._carregar_cardapio()
        )

        familias = CacheManager.get_familias()
        opcoes = [ft.dropdown.Option(key=0, text="Todas as famílias")]
        opcoes += [
            ft.dropdown.Option(key=f.ID_FAMILIA, text=f.DESCRICAO_FAMILIA)
            for f in familias
        ]
        self.cb_familia = zDropdown(
            label="Família",
            options=opcoes,
            width=260,
            on_change=lambda e: self._carregar_cardapio()
        )
        self.cb_familia.value = 0

        self.btn_pesq = ft.IconButton(
            icon=ft.icons.SEARCH,
            bgcolor=AppConfig.BTN_PRIMARY,
            icon_color="#ffffff",
            tooltip="Pesquisar",
            on_click=lambda e: self._carregar_cardapio()
        )

        self.btn_sacola = ft.ElevatedButton(
            text="0",
            icon=ft.icons.SHOPPING_BAG,
            bgcolor=ft.colors.RED_500,
            icon_color="#ffffff",
            color="#ffffff",
            height=42,
            tooltip="Ver sacola",
            on_click=lambda e: self.page.go("/cliente")
        )

        self.col_cardapio = ft.ListView(
            padding=0,
            spacing=8,
            controls=[],
            auto_scroll=False,
            on_scroll=self._on_scroll_cardapio,
            on_scroll_interval=120,
            expand=True,
        )

        self.progress = ft.ProgressRing(
            width=24, height=24, stroke_width=3,
            color=AppConfig.BTN_PRIMARY,
            visible=False
        )

    def _build_layout(self):
        bg = AppConfig.BG_COLOR

        self.panel = ft.View(
            route="/cardapio",
            bgcolor=bg,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.top_center,
                    content=ft.Container(
                        width=760,
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        content=ft.Column(
                            expand=True,
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Row(
                                    [
                                        zTitle("🍺  Cardápio"),
                                        self.btn_sacola,
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                zDivider(),
                                ft.Row(
                                    [self.cb_familia, self.txt_pesq, self.btn_pesq, self.progress],
                                    wrap=True,
                                    spacing=8,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                self.col_cardapio,
                            ],
                        ),
                    ),
                )
            ],
        )

    # ─── Carregamento ───────────────────────────────────────────

    def _carregar_familias(self):
        familias = CacheManager.get_familias()
        opcoes = [ft.dropdown.Option(key=0, text="Todas as famílias")]
        opcoes += [
            ft.dropdown.Option(key=f.ID_FAMILIA, text=f.DESCRICAO_FAMILIA)
            for f in familias
        ]
        self.cb_familia.options = opcoes
        self.cb_familia.value = 0
        try:
            self.cb_familia.update()
        except Exception:
            pass

    def _carregar_cardapio(self):
        self._show_progress(True)

        nome = (self.txt_pesq.value or "").strip()
        try:
            id_familia = int(self.cb_familia.value or 0)
        except (ValueError, TypeError):
            id_familia = 0

        lista = CacheManager.filtrar_produtos(nome=nome, id_familia=id_familia)
        self._produtos_filtrados = lista
        self._indice_carregado = 0
        self._qtde_map.clear()
        self.col_cardapio.controls.clear()
        self._renderizar_proxima_pagina(scroll_top=True)
        self._garantir_rolagem_inicial()

        self._show_progress(False)

    def _carregar_proxima_pagina(self):
        self._renderizar_proxima_pagina(scroll_top=False)

    def _renderizar_proxima_pagina(self, scroll_top: bool = False):
        if self._carregando_pagina:
            return

        self._carregando_pagina = True
        inicio = self._indice_carregado
        fim = min(inicio + self._tam_pagina, len(self._produtos_filtrados))

        if inicio >= fim:
            self._carregando_pagina = False
            return

        bloco = self._produtos_filtrados[inicio:fim]
        self.col_cardapio.controls.extend([self._get_row_card(produto) for produto in bloco])
        self._indice_carregado = fim

        try:
            self.col_cardapio.update()
            if scroll_top:
                self.col_cardapio.scroll_to(offset=0)
        except Exception:
            pass
        self._carregando_pagina = False

    def _garantir_rolagem_inicial(self):
        if self._indice_carregado >= len(self._produtos_filtrados):
            return

        # Em telas altas, carrega mais um lote para garantir área rolável.
        if len(self.col_cardapio.controls) <= 8:
            self._carregar_proxima_pagina()

    def _on_scroll_cardapio(self, e: ft.OnScrollEvent):
        if self._carregando_pagina:
            return

        if self._indice_carregado >= len(self._produtos_filtrados):
            return

        try:
            posicao = float(e.pixels)
            limite = float(e.max_scroll_extent)
        except Exception:
            return

        # Carrega próximo lote quando o usuário estiver próximo ao fim da lista.
        if limite > 0 and posicao >= (limite - 180):
            self._carregar_proxima_pagina()

    def _get_row_card(self, produto) -> ft.Row:
        return ft.Row(
            controls=[self._get_card(produto)],
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _extrair_base64_foto(self, foto_produto: str) -> str:
        if not foto_produto:
            return ""

        foto_limpa = str(foto_produto).strip()
        if not foto_limpa:
            return ""

        if foto_limpa.startswith("data:image") and "," in foto_limpa:
            foto_limpa = foto_limpa.split(",", 1)[1]

        return foto_limpa.replace("\n", "").replace("\r", "").strip()

    def _get_foto_control(self, produto) -> ft.Control:
        foto_base64 = self._extrair_base64_foto(getattr(produto, "FOTO_PRODUTO", ""))

        if foto_base64:
            return ft.Container(
                width=288,
                height=182,
                border_radius=8,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=ft.Image(
                    src_base64=foto_base64,
                    fit=ft.ImageFit.COVER,
                    width=288,
                    height=182,
                    error_content=ft.Container(
                        alignment=ft.alignment.center,
                        bgcolor="#f5f5f5",
                        content=ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED_OUTLINED, color=ft.colors.GREY_500),
                    ),
                ),
            )

        return ft.Container(
            width=288,
            height=182,
            border_radius=8,
            bgcolor="#f5f5f5",
            alignment=ft.alignment.center,
            content=ft.Icon(ft.icons.IMAGE_OUTLINED, color=ft.colors.GREY_500),
        )

    def _get_card(self, produto) -> ft.Container:
        # Quantidade atual na sacola
        existing = [it for it in self.sacola.ITEMS if it.ID_PRODUTO == produto.ID_PRODUTO]
        qtde_atual = existing[0].QTDE if existing else 0

        txt_qtde = ft.TextField(
            value=str(qtde_atual),
            width=78,
            height=42,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            color="#333333",
            bgcolor="#ffffff",
            border_color=AppConfig.FONT_COLOR,
        )
        self._qtde_map[produto.ID_PRODUTO] = txt_qtde

        btn_minus = ft.IconButton(
            icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
            icon_color=AppConfig.BTN_PRIMARY,
            icon_size=34,
            tooltip="Diminuir",
            on_click=lambda e, p=produto, t=txt_qtde: self._subtrair(p, t)
        )
        btn_plus = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE_OUTLINE,
            icon_color=AppConfig.BTN_PRIMARY,
            icon_size=34,
            tooltip="Adicionar",
            on_click=lambda e, p=produto, t=txt_qtde: self._adicionar(p, t)
        )

        preco_fmt = format_currency(produto.PRECO_DELIVERY)

        card_content = ft.Column(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=4,
            controls=[
                self._get_foto_control(produto),
                ft.Container(
                    width=288,
                    height=52,
                    content=ft.Text(
                        produto.DESCRICAO_PRODUTO,
                        size=15,
                        color=AppConfig.FONT_COLOR,
                        weight=ft.FontWeight.BOLD,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        width=288,
                    ),
                ),
                ft.Text(preco_fmt, size=18, color=AppConfig.FONT_COLOR, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [btn_minus, txt_qtde, btn_plus],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
            ],
        )

        return ft.Container(
            content=card_content,
            bgcolor="#ffffff",
            border_radius=10,
            padding=12,
            width=320,
            height=336,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color=ft.colors.GREY_300),
        )

    # ─── Sacola ─────────────────────────────────────────────────

    def _adicionar(self, produto, txt_qtde: ft.TextField):
        try:
            val = int(txt_qtde.value or 0)
        except ValueError:
            val = 0
        val += 1
        txt_qtde.value = str(val)
        try:
            txt_qtde.update()
        except Exception:
            pass
        self._atualizar_item_sacola(produto, val)

    def _subtrair(self, produto, txt_qtde: ft.TextField):
        try:
            val = int(txt_qtde.value or 0)
        except ValueError:
            val = 0
        val = max(0, val - 1)
        txt_qtde.value = str(val)
        try:
            txt_qtde.update()
        except Exception:
            pass
        self._atualizar_item_sacola(produto, val)

    def _atualizar_item_sacola(self, produto, qtde: int):
        existing = [it for it in self.sacola.ITEMS if it.ID_PRODUTO == produto.ID_PRODUTO]
        total_item = round(qtde * produto.PRECO_DELIVERY, 2)

        if existing:
            if qtde == 0:
                self.sacola.ITEMS.remove(existing[0])
            else:
                existing[0].QTDE = qtde
                existing[0].PRECO_UNITARIO = produto.PRECO_DELIVERY
                existing[0].TOTAL_ITEM = total_item
        elif qtde > 0:
            self.sacola.ITEMS.append(
                ItemPedido(
                    ID_PRODUTO=produto.ID_PRODUTO,
                    DESCRICAO_PRODUTO=produto.DESCRICAO_PRODUTO,
                    QTDE=qtde,
                    PRECO_UNITARIO=produto.PRECO_DELIVERY,
                    TOTAL_ITEM=total_item,
                )
            )

        total_itens = sum(it.QTDE for it in self.sacola.ITEMS)
        self.btn_sacola.text = str(total_itens)
        try:
            self.btn_sacola.update()
        except Exception:
            pass

    def resetar_qtdes(self):
        """Reseta quantidades exibidas no cardápio conforme a sacola atual."""
        for id_produto, txt in self._qtde_map.items():
            existing = [it for it in self.sacola.ITEMS if it.ID_PRODUTO == id_produto]
            txt.value = str(existing[0].QTDE if existing else 0)
            try:
                txt.update()
            except Exception:
                pass
        total_itens = sum(it.QTDE for it in self.sacola.ITEMS)
        self.btn_sacola.text = str(total_itens)
        try:
            self.btn_sacola.update()
        except Exception:
            pass

    # ─── Helpers ────────────────────────────────────────────────

    def _show_progress(self, visible: bool):
        self.progress.visible = visible
        try:
            self.progress.update()
        except Exception:
            pass
