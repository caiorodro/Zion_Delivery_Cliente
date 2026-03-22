class AppConfig:
    # URL da API backend
    URL_API = "http://localhost:8000"

    # Cores do tema
    BG_COLOR = "#a7b1b6"
    FONT_COLOR = "#874531"
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
