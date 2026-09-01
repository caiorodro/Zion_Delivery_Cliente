import threading

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
        self._qtde_map: dict = {}   # chave do produto -> TextField
        self._produtos_filtrados = []
        self._indice_carregado = 0
        self._tam_pagina = 30
        self._limite_atalhos_ultimo_pedido = 6
        self._limite_atalhos_historico = 6
        self._carregando_pagina = False
        self._ordenacao_inicial_aplicada = False
        self._cliente_identificado = False
        self._id_familia_sel = 0
        self._menu_aberto = False
        self._init_controls()
        self._build_layout()
        self._build_menu_familias()
        self._carregar_cardapio()

    # ─── Inicialização ──────────────────────────────────────────

    def _init_controls(self):
        self.txt_pesq = zTextField(
            label="Pesquisar produto...",
            width=260,
            autofocus=True,
            on_change=lambda e: self._on_change_busca(),
            on_submit=lambda e: self._carregar_cardapio()
        )
        self._busca_seq = 0

        self.btn_limpar_pesq = ft.IconButton(
            icon=ft.icons.CLOSE,
            icon_size=18,
            icon_color=AppConfig.FONT_COLOR,
            tooltip="Limpar busca",
            visible=False,
            on_click=lambda e: self._limpar_busca(),
        )
        self.txt_pesq.suffix = self.btn_limpar_pesq

        self.menu_familias = ft.Column(
            controls=[],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        self.btn_pesq = ft.IconButton(
            icon=ft.icons.SEARCH,
            bgcolor=AppConfig.BTN_PRIMARY,
            icon_color="#ffffff",
            tooltip="Pesquisar",
            on_click=lambda e: self._carregar_cardapio()
        )

        self.btn_menu = ft.IconButton(
            icon=ft.icons.MENU,
            icon_color=AppConfig.BTN_PRIMARY,
            tooltip="Categorias",
            on_click=lambda e: self._toggle_menu(),
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

        self.lbl_recentes = zLabel("Sugestoes rapidas", size=15, bold=True)
        self.lbl_ultimo_pedido = zLabel("Pedir novamente", size=13, bold=True)
        self.row_ultimo_pedido = ft.Row(
            controls=[],
            wrap=True,
            spacing=8,
            run_spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        self.lbl_historico = zLabel("Mais vendidos da loja", size=13, bold=True)
        self.row_historico = ft.Row(
            controls=[],
            wrap=True,
            spacing=8,
            run_spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        )
        self.ctn_recentes = ft.Container(
            visible=False,
            padding=ft.padding.only(top=4, bottom=4),
            content=ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self.lbl_recentes,
                    self.lbl_ultimo_pedido,
                    self.row_ultimo_pedido,
                    self.lbl_historico,
                    self.row_historico,
                ],
            ),
        )

    def _build_layout(self):
        bg = AppConfig.BG_COLOR

        self.menu_lateral = ft.Container(
            width=210,
            visible=self._menu_aberto,
            padding=ft.padding.only(right=12, top=4),
            content=ft.Column(
                expand=True,
                spacing=10,
                controls=[
                    zLabel("Categorias", size=15, bold=True),
                    self.menu_familias,
                ],
            ),
        )
        self.divisor_menu = ft.VerticalDivider(
            width=1, color=AppConfig.FONT_COLOR, visible=self._menu_aberto,
        )

        conteudo = ft.Column(
            expand=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.ctn_recentes,
                self.col_cardapio,
            ],
        )

        self.panel = ft.View(
            route="/cardapio",
            bgcolor=bg,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.top_center,
                    content=ft.Container(
                        width=940,
                        padding=ft.padding.symmetric(horizontal=16, vertical=12),
                        content=ft.Column(
                            expand=True,
                            spacing=10,
                            controls=[
                                ft.Row(
                                    [
                                        ft.Row(
                                            [self.btn_menu, zTitle("🍺  Cardápio")],
                                            spacing=4,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        self.btn_sacola,
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                zDivider(),
                                ft.Row(
                                    [self.txt_pesq, self.btn_pesq, self.progress],
                                    wrap=True,
                                    spacing=8,
                                    alignment=ft.MainAxisAlignment.START,
                                ),
                                ft.Row(
                                    expand=True,
                                    vertical_alignment=ft.CrossAxisAlignment.START,
                                    controls=[
                                        self.menu_lateral,
                                        self.divisor_menu,
                                        ft.Container(expand=True, content=conteudo),
                                    ],
                                ),
                            ],
                        ),
                    ),
                )
            ],
        )

    # ─── Carregamento ───────────────────────────────────────────

    def _build_menu_familias(self):
        familias = CacheManager.get_familias()
        itens = [(0, "Todas as famílias")]
        itens += [(f.ID_FAMILIA, f.DESCRICAO_FAMILIA) for f in familias]
        self.menu_familias.controls = [
            self._criar_btn_familia(id_familia, descricao)
            for id_familia, descricao in itens
        ]
        try:
            self.menu_familias.update()
        except Exception:
            pass

    def _criar_btn_familia(self, id_familia: int, descricao: str) -> ft.Control:
        selecionado = int(id_familia or 0) == int(self._id_familia_sel or 0)
        return ft.Container(
            width=200,
            bgcolor=AppConfig.BTN_PRIMARY if selecionado else "#ffffff",
            border=ft.border.all(1, AppConfig.BTN_PRIMARY),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            ink=True,
            on_click=lambda e, i=id_familia: self._selecionar_familia(i),
            content=ft.Text(
                descricao,
                size=14,
                color="#ffffff" if selecionado else AppConfig.FONT_COLOR,
                weight=ft.FontWeight.BOLD,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        )

    def _selecionar_familia(self, id_familia: int):
        self._id_familia_sel = int(id_familia or 0)
        self._menu_aberto = False
        self._build_menu_familias()
        self._aplicar_estado_menu()
        self._carregar_cardapio()

    def _toggle_menu(self):
        self._menu_aberto = not self._menu_aberto
        self._aplicar_estado_menu()

    def _aplicar_estado_menu(self):
        self.menu_lateral.visible = self._menu_aberto
        self.divisor_menu.visible = self._menu_aberto
        self.btn_menu.icon = ft.icons.MENU_OPEN if self._menu_aberto else ft.icons.MENU
        for ctrl in (self.menu_lateral, self.divisor_menu, self.btn_menu):
            try:
                ctrl.update()
            except Exception:
                pass

    def _aplicar_ordenacao_inicial(self):
        if self._ordenacao_inicial_aplicada:
            return

        self._ordenacao_inicial_aplicada = True

        telefone = str(getattr(self.sacola.DADOS_CLIENTE, "TELEFONE", "") or "").strip()
        cpf = str(getattr(self.sacola.DADOS_CLIENTE, "CPF", "") or "").strip()

        if not telefone and not cpf:
            try:
                dados_salvos = self.page.client_storage.get("zion_cliente_v1")
            except Exception:
                dados_salvos = None

            if isinstance(dados_salvos, dict):
                telefone = str(dados_salvos.get("TELEFONE") or "").strip()
                cpf = str(dados_salvos.get("CPF") or "").strip()

        self._cliente_identificado = bool(telefone or cpf)

        if telefone or cpf:
            try:
                CacheManager.download_e_salvar(cpf=cpf, telefone=telefone)
            except Exception:
                pass

        self._atualizar_botoes_recentes()

    def _on_change_busca(self):
        """Filtra enquanto o usuario digita, com um pequeno atraso (debounce)."""
        tem_texto = bool((self.txt_pesq.value or "").strip())
        if self.btn_limpar_pesq.visible != tem_texto:
            self.btn_limpar_pesq.visible = tem_texto
            try:
                self.btn_limpar_pesq.update()
            except Exception:
                pass

        self._busca_seq += 1
        seq = self._busca_seq

        def _disparar():
            if seq == self._busca_seq:
                self._carregar_cardapio()

        timer = threading.Timer(0.35, _disparar)
        timer.daemon = True
        timer.start()

    def _limpar_busca(self):
        """Limpa o campo de busca e recarrega o cardapio completo."""
        self._busca_seq += 1  # cancela qualquer debounce pendente
        self.txt_pesq.value = ""
        self.btn_limpar_pesq.visible = False
        try:
            self.txt_pesq.update()
            self.btn_limpar_pesq.update()
        except Exception:
            pass
        self._carregar_cardapio()

    def _carregar_cardapio(self):
        self._show_progress(True)
        self._aplicar_ordenacao_inicial()

        nome = (self.txt_pesq.value or "").strip()

        # Busca por texto livre ignora o filtro de familia: volta para "Todas as familias".
        if nome and int(self._id_familia_sel or 0) != 0:
            self._id_familia_sel = 0
            self._build_menu_familias()

        id_familia = int(self._id_familia_sel or 0)

        lista = CacheManager.filtrar_produtos(nome=nome, id_familia=id_familia)
        self._produtos_filtrados = lista
        self._indice_carregado = 0
        self._qtde_map.clear()
        self.col_cardapio.controls.clear()
        self._atualizar_botoes_recentes()
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

    def _atualizar_botoes_recentes(self):
        produtos_base = CacheManager.get_produtos()

        if not produtos_base:
            self.row_ultimo_pedido.controls = []
            self.row_historico.controls = []
            self.lbl_ultimo_pedido.visible = False
            self.row_ultimo_pedido.visible = False
            self.lbl_historico.visible = False
            self.row_historico.visible = False
            self.ctn_recentes.visible = False
            try:
                self.row_ultimo_pedido.update()
                self.row_historico.update()
                self.ctn_recentes.update()
            except Exception:
                pass
            return

        codigos_usados = set()
        ultimo_pedido = []
        mais_vendidos = []

        for produto in produtos_base:
            produto_key = self._get_produto_key(produto)
            if produto_key in codigos_usados:
                continue

            if int(getattr(produto, "EM_ULTIMO_PEDIDO", 0) or 0) == 1:
                codigos_usados.add(produto_key)
                ultimo_pedido.append(produto)
                if len(ultimo_pedido) >= self._limite_atalhos_ultimo_pedido:
                    break

        if ultimo_pedido:
            self.row_ultimo_pedido.controls = [
                self._criar_chip_produto_recente(produto, destaque="ultimo") for produto in ultimo_pedido
            ]
            self.row_historico.controls = []
            self.lbl_ultimo_pedido.visible = True
            self.row_ultimo_pedido.visible = True
            self.lbl_historico.visible = False
            self.row_historico.visible = False
            self.ctn_recentes.visible = True
        else:
            for produto in produtos_base:
                produto_key = self._get_produto_key(produto)
                if produto_key in codigos_usados:
                    continue

                if int(getattr(produto, "QTDE_VENDIDA_15D", 0) or 0) > 0:
                    codigos_usados.add(produto_key)
                    mais_vendidos.append(produto)
                    if len(mais_vendidos) >= self._limite_atalhos_historico:
                        break

            self.row_ultimo_pedido.controls = []
            self.row_historico.controls = [
                self._criar_chip_produto_recente(produto, destaque="historico") for produto in mais_vendidos
            ]
            self.lbl_ultimo_pedido.visible = False
            self.row_ultimo_pedido.visible = False
            self.lbl_historico.visible = bool(mais_vendidos)
            self.row_historico.visible = bool(mais_vendidos)
            self.ctn_recentes.visible = bool(mais_vendidos)

        try:
            self.lbl_ultimo_pedido.update()
            self.row_ultimo_pedido.update()
            self.lbl_historico.update()
            self.row_historico.update()
            self.ctn_recentes.update()
        except Exception:
            pass

    def _criar_chip_produto_recente(self, produto, destaque: str) -> ft.Control:
        descricao = str(getattr(produto, "DESCRICAO_PRODUTO", "") or "").strip()
        texto = descricao if len(descricao) <= 24 else f"{descricao[:21].rstrip()}..."
        preco = format_currency(getattr(produto, "PRECO_DELIVERY", 0) or 0)
        badge_texto = "Ultimo pedido" if destaque == "ultimo" else "Sugestao"
        badge_bg = "#ead3c4" if destaque == "ultimo" else "#dbe7ea"

        return ft.Container(
            width=174,
            bgcolor="#ffffff",
            border=ft.border.all(1, AppConfig.BTN_PRIMARY),
            border_radius=16,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            ink=True,
            on_click=lambda e, p=produto: self._adicionar_produto_recente(p),
            tooltip=f"Adicionar {descricao}",
            content=ft.Column(
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(
                        bgcolor=badge_bg,
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        content=ft.Text(
                            badge_texto,
                            size=10,
                            color=AppConfig.FONT_COLOR,
                            weight=ft.FontWeight.W_600,
                        ),
                    ),
                    ft.Text(
                        texto,
                        size=13,
                        color=AppConfig.FONT_COLOR,
                        weight=ft.FontWeight.BOLD,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        preco,
                        size=12,
                        color=AppConfig.FONT_COLOR,
                    ),
                ],
            ),
        )

    def _adicionar_produto_recente(self, produto):
        produto_key = self._get_produto_key(produto)
        txt_qtde = self._qtde_map.get(produto_key)
        if txt_qtde is not None:
            self._adicionar(produto, txt_qtde)
            return

        existing = [it for it in self.sacola.ITEMS if self._get_item_key(it) == produto_key]
        qtde = (existing[0].QTDE if existing else 0) + 1
        self._atualizar_item_sacola(produto, qtde)

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
                bgcolor="#ffffff",
                content=ft.Image(
                    src_base64=foto_base64,
                    fit=ft.ImageFit.CONTAIN,
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
        produto_key = self._get_produto_key(produto)
        existing = [it for it in self.sacola.ITEMS if self._get_item_key(it) == produto_key]
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
            on_change=lambda e, p=produto: self._on_change_qtde(e, p),
        )
        self._qtde_map[produto_key] = txt_qtde

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
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.colors.with_opacity(0.28, ft.colors.BLACK),
                offset=ft.Offset(-5, 5),
            ),
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

    def _on_change_qtde(self, e: ft.ControlEvent, produto):
        raw_val = str(e.control.value or "").strip()
        digits_only = "".join(ch for ch in raw_val if ch.isdigit())

        if raw_val != digits_only:
            e.control.value = digits_only
            try:
                e.control.update()
            except Exception:
                pass

        qtde = int(digits_only) if digits_only else 0
        self._atualizar_item_sacola(produto, qtde)

    def _atualizar_item_sacola(self, produto, qtde: int):
        produto_key = self._get_produto_key(produto)
        existing = [it for it in self.sacola.ITEMS if self._get_item_key(it) == produto_key]
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
                    CODIGO_WABIZ=produto.CODIGO_WABIZ,
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
        for produto_key, txt in self._qtde_map.items():
            existing = [it for it in self.sacola.ITEMS if self._get_item_key(it) == produto_key]
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

    def _get_produto_key(self, produto) -> str:
        return f"produto:{int(getattr(produto, 'ID_PRODUTO', 0) or 0)}"

    def _get_item_key(self, item) -> str:
        return f"produto:{int(getattr(item, 'ID_PRODUTO', 0) or 0)}"
