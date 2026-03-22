import mysql.connector
from mysql.connector import pooling
from cfg.config import Config


_pool = None


def get_pool():
    global _pool
    if _pool is None:
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
    return _pool


def get_connection():
    return get_pool().get_connection()
