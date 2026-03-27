import mysql.connector
from mysql.connector import pooling
from cfg.config import Config


_pool = None


def get_connection_string(mask_password: bool = True) -> str:
    if mask_password:
        return Config.DB_CONNECTION_URL_SAFE
    return Config.DB_CONNECTION_URL


def get_pool():
    global _pool
    if _pool is None:
        print(f"[DB] Criando pool MySQL com conexao: {get_connection_string(mask_password=True)}")
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="zion_pool",
                pool_size=5,
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USERNAME,
                password=Config.DB_PASSWORD,
                charset="utf8mb4",
                collation="utf8mb4_general_ci",
                use_pure=True,
            )
        except Exception as ex:
            print(f"[DB] Falha ao criar pool MySQL: {get_connection_string(mask_password=True)}")
            raise
    return _pool


def get_connection():
    return get_pool().get_connection()
