import threading
import flet as ft

from frontend.base.cache import CacheManager
from frontend.cfg.config import AppConfig
from frontend.models.sacola import Sacola
from frontend.style.zControls import zLabel, zTitle
from frontend.views.endereco import Endereco
from frontend.views.cardapio import Cardapio
from frontend.views.cliente import Cliente
from frontend.views.pagamento import Pagamento
from frontend.views.confirmacao import Confirmacao


def main(page: ft.Page):
    page.title = "Zion Delivery"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = AppConfig.BG_COLOR
    page.padding = 0

    # ─── Estado global do pedido ────────────────────────────────
    sacola = Sacola()
    sacola.TAXA_ENTREGA = AppConfig.TAXA_ENTREGA

    # ─── Splash / Loading ───────────────────────────────────────
    progress_ring = ft.ProgressRing(
        width=48, height=48, stroke_width=4,
        color=AppConfig.BTN_PRIMARY,
    )
    lbl_loading = zLabel("Baixando cardápio...", size=14, color=AppConfig.FONT_COLOR)
    splash = ft.View(
        route="/splash",
        bgcolor=AppConfig.BG_COLOR,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Image(
                        src="frontend/img/logo.png",
                        width=180,
                        error_content=zTitle("🍺 ZION"),
                    ),
                    ft.Container(height=20),
                    progress_ring,
                    ft.Container(height=10),
                    lbl_loading,
                ],
            )
        ],
    )

    # ─── Instâncias das views ───────────────────────────────────
    view_endereco: Endereco = None
    view_cardapio: Cardapio = None
    view_cliente: Cliente = None
    view_pagamento: Pagamento = None
    view_confirmacao: Confirmacao = None

    def get_view_endereco():
        nonlocal view_endereco
        if view_endereco is None:
            view_endereco = Endereco(page, sacola)
        return view_endereco

    def get_view_cardapio():
        nonlocal view_cardapio

        if view_cardapio is None:
            view_cardapio = Cardapio(page, sacola)

        return view_cardapio

    def get_view_cliente():
        nonlocal view_cliente

        if view_cliente is None:
            view_cliente = Cliente(page, sacola)

        return view_cliente

    def get_view_pagamento():
        nonlocal view_pagamento
        if view_pagamento is None:
            view_pagamento = Pagamento(page, sacola)
        return view_pagamento

    def get_view_confirmacao():
        nonlocal view_confirmacao
        if view_confirmacao is None:
            view_confirmacao = Confirmacao(page, sacola)
        return view_confirmacao

    # ─── Roteamento ─────────────────────────────────────────────
    def route_change(route):
        page.views.clear()

        r = page.route

        if r == "/splash" or r == "/":
            page.views.append(splash)

        elif r == "/endereco":
            page.views.append(get_view_endereco().panel)

        elif r == "/cardapio":
            cv = get_view_cardapio()
            cv.resetar_qtdes()
            page.views.append(cv.panel)

        elif r == "/cliente":
            if not sacola.ITEMS:
                page.go("/cardapio")
                return
            cl = get_view_cliente()
            cl.carregar_dados()
            page.views.append(cl.panel)

        elif r == "/pagamento":
            if not sacola.DADOS_CLIENTE.NOME_CLIENTE:
                page.go("/cliente")
                return
            pg = get_view_pagamento()
            pg.carregar_dados()
            page.views.append(pg.panel)

        elif r == "/confirmacao":
            if not sacola.PAGAMENTO.FORMA_PAGAMENTO:
                page.go("/pagamento")
                return
            cf = get_view_confirmacao()
            cf.carregar_dados()
            page.views.append(cf.panel)

        page.update()

    page.on_route_change = route_change

    # ─── Download inicial do cardápio ───────────────────────────
    def _init_data():
        # Tenta carregar cache local primeiro
        if CacheManager.carregar_cache_local():
            lbl_loading.value = "Cache carregado! Atualizando..."
            try:
                lbl_loading.update()
            except Exception:
                pass

        # Baixa da API
        ok = CacheManager.download_e_salvar()
        if not ok and not CacheManager.is_loaded():
            lbl_loading.value = "⚠ Sem conexão. Tente novamente."
            try:
                lbl_loading.update()
            except Exception:
                pass
            return

        # Navega para a tela de endereço
        page.go("/endereco")

    page.views.append(splash)
    page.go("/splash")

    threading.Thread(target=_init_data, daemon=True).start()


ft.app(
    target=main,
    view=ft.WEB_BROWSER,
    port=8080,
    assets_dir="frontend/img",
)
