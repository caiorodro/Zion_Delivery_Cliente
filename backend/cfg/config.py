class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = "ZionDelivery@2026#SecretKey!xYz"

    DB_HOST = "localhost"
    DB_PORT = 3306
    DB_NAME = "zion"
    DB_USERNAME = "root"
    DB_PASSWORD = "56Runna01"

    DB_CONNECTION_URL = (
        f"mysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    DB_CONNECTION_URL_SAFE = (
        f"mysql://{DB_USERNAME}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    API_HOST = "0.0.0.0"
    API_PORT = 8000

    # Taxa de entrega padrão (pode ser dinâmica no futuro)
    TAXA_ENTREGA = 5.00

    # URL base da API (para o frontend apontar)
    URL_API = "http://localhost:8000"

    # Tempo limite (segundos) para polling de status do pedido
    POLLING_TIMEOUT = 180
    POLLING_INTERVAL = 5


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    API_HOST = "0.0.0.0"
