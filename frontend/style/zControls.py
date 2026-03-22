import flet as ft
from frontend.cfg.config import AppConfig

COLORS = getattr(ft, "colors", ft.Colors)


BG = AppConfig.BG_COLOR
FONT = AppConfig.FONT_COLOR
BTN = AppConfig.BTN_PRIMARY


class zButton(ft.ElevatedButton):
    def __init__(self, text: str, on_click=None, width: int = None, icon=None,
                 visible: bool = True):
        super().__init__()
        self.text = text
        self.bgcolor = BTN
        self.color = "#ffffff"
        self.on_click = on_click
        self.visible = visible
        if width:
            self.width = width
        if icon:
            self.icon = icon
            self.icon_color = "#ffffff"


class zOutlineButton(ft.OutlinedButton):
    def __init__(self, text: str, on_click=None):
        super().__init__()
        self.text = text
        self.on_click = on_click
        self.style = ft.ButtonStyle(
            color=FONT,
            side=ft.BorderSide(2, FONT),
        )


class zTextField(ft.TextField):
    def __init__(self, label: str, width: int = 250, keyboard_type=None,
                 hint_text: str = None, on_change=None, on_submit=None,
                 autofocus: bool = False, read_only: bool = False,
                 max_length: int = None, visible: bool = True):
        super().__init__()
        self.label = label
        self.label_style = ft.TextStyle(color=FONT, weight=ft.FontWeight.BOLD)
        self.width = width
        self.bgcolor = AppConfig.INPUT_BG
        self.color = "#333333"
        self.border_color = FONT
        self.focused_border_color = BTN
        self.cursor_color = FONT
        self.hint_text = hint_text
        self.autofocus = autofocus
        self.read_only = read_only
        self.visible = visible
        
        if keyboard_type:
            self.keyboard_type = keyboard_type
        if on_change:
            self.on_change = on_change
        if on_submit:
            self.on_submit = on_submit
        if max_length:
            self.max_length = max_length


class zDropdown(ft.Dropdown):
    def __init__(self, label: str, options: list = None, width: int = 250, on_change=None):
        super().__init__()
        self.label = label
        self.label_style = ft.TextStyle(color=FONT, weight=ft.FontWeight.BOLD)
        self.width = width
        self.bgcolor = AppConfig.INPUT_BG
        self.color = "#333333"
        self.border_color = FONT
        self.focused_border_color = BTN
        self.options = options or []
        if on_change:
            self.on_change = on_change


class zLabel(ft.Text):
    def __init__(self, value: str, size: int = 16, bold: bool = False, color: str = None):
        super().__init__()
        self.value = value
        self.color = color or FONT
        self.size = size
        if bold:
            self.weight = ft.FontWeight.BOLD


class zTitle(ft.Text):
    def __init__(self, value: str):
        super().__init__()
        self.value = value
        self.color = FONT
        self.size = 22
        self.weight = ft.FontWeight.BOLD


class zCard(ft.Card):
    def __init__(self, content: ft.Control, expand: bool = False):
        super().__init__()
        self.color = AppConfig.CARD_BG
        self.elevation = 3
        self.content = ft.Container(
            content=content,
            padding=12,
        )
        if expand:
            self.expand = True


class zDivider(ft.Divider):
    def __init__(self):
        super().__init__()
        self.color = FONT
        self.thickness = 1


class zBanner(ft.Banner):
    def __init__(self, text: str, page: ft.Page):
        super().__init__()
        self.bgcolor = COLORS.AMBER_100
        self.leading = ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=COLORS.AMBER_900, size=40)
        self.content = ft.Text(text, color=COLORS.AMBER_900, size=14)
        self.actions = [
            ft.TextButton("OK", on_click=lambda e: page.close(self))
        ]
        self.btnOk = self.actions[0]


class zSnackBar(ft.SnackBar):
    def __init__(self, text: str, error: bool = False):
        super().__init__(content=ft.Text(text, color=COLORS.WHITE))
        self.bgcolor = "#455A64"
        self.duration = 3000
