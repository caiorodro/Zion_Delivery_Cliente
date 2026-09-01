import os


class AppConfig:
    # URL da API backend
    # Prioridade:
    # 1) ZION_URL_API
    # 2) URL_API
    # 3) fallback local
    URL_API = (
        os.getenv("ZION_URL_API")
        or os.getenv("URL_API")
        or "http://localhost:8000"
    ).rstrip("/")

    # Cores do tema
    BG_COLOR = "#ffffff"
    FONT_COLOR = "#333333"
    BTN_PRIMARY = "#874531"
    BTN_TEXT = "#ffffff"
    CARD_BG = "#ffffff"
    INPUT_BG = "#ffffff"

    # Taxa de entrega padrão
    TAXA_ENTREGA = 5.00
    TAXA_ENTREGA_FALLBACK = 5.00

    # Polling de status do pedido
    POLLING_TIMEOUT = 180   # segundos
    POLLING_INTERVAL = 5    # segundos

    # Arquivo local de cache de produtos
    CACHE_PRODUTOS = "frontend/data/produtos.json"
    CACHE_FAMILIAS = "frontend/data/familias.json"
    CACHE_GRADES = "frontend/data/grades.json"

    # Configuração local da loja (lat/lon e fallback de frete)
    LOJA_CONFIG = "frontend/data/loja_config.json"
    FRETE_REGRAS_CONFIG = "frontend/data/frete_regras.json"

    # Logging
    LOG_DIR = "/tmp"
    LOG_FILE = "/tmp/frontend.log"
    LOG_LEVEL = "INFO"

    # Google Maps Geocoding API
    GOOGLE_MAPS_API_KEY = "AIzaSyBFfl6HmN9U8QuAU9xIejjhkn46EkZNSPY"
