import base64
from typing import List
from decimal import Decimal

from base.database import get_connection
from base.qBase import qBase
from models.produto import Produto
from models.familia_produto import FamiliaProduto
from models.grade_produto import GradeProduto

class ProdutoView:

    def __init__(self):
        self.qbase = qBase()

    async def get_all_produtos(self) -> List[dict]:
        """Retorna todos os produtos ativos com preço delivery > 0."""
        conn = get_connection()

        try:
            cursor = conn.cursor()

            historico_join = f"""
                LEFT JOIN (
                    SELECT
                        ip.ID_PRODUTO,
                        SUM(ip.QTDE) AS QTDE_VENDIDA
                    FROM tb_item_pedido ip
                    INNER JOIN tb_pedido p
                        ON p.NUMERO_PEDIDO = ip.NUMERO_PEDIDO
                    WHERE p.STATUS_PEDIDO = 3
                        AND p.DATA_HORA < CURDATE()
                    GROUP BY ip.ID_PRODUTO
                ) h ON h.ID_PRODUTO = p.ID_PRODUTO
            """

            sql = """
                SELECT
                    p.ID_PRODUTO,
                    p.DESCRICAO_PRODUTO,
                    p.PRECO_BALCAO,
                    p.ID_FAMILIA,
                    p.PRODUTO_ATIVO,
                    p.FOTO_PRODUTO
                FROM tb_produto p
            """

            sql += historico_join

            sql += " WHERE p.PRODUTO_ATIVO = 1"

            if historico_join:
                sql += " ORDER BY COALESCE(h.QTDE_VENDIDA, 0) DESC, p.DESCRICAO_PRODUTO"
            else:
                sql += " ORDER BY p.DESCRICAO_PRODUTO"

            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()

            result = []
            for row in rows:
                result.append(
                    Produto(
                        ID_PRODUTO=row[0],
                        DESCRICAO_PRODUTO=row[1],
                        PRECO_DELIVERY=float(row[2]) if isinstance(row[2], Decimal) else (row[2] or 0.0),
                        ID_FAMILIA=row[3],
                        PRODUTO_ATIVO=row[4],
                        FOTO_PRODUTO=self.resolveImage(row[5])
                    ).__dict__
                )

            return result
        finally:
            conn.close()

    def _resolver_tabelas_historico(self, cursor):
        """Resolve os nomes das tabelas de pedidos e itens disponíveis no banco."""
        cursor.execute(
            """
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME IN (
                    'tb_pedido',
                    'tb_item_pedido',
                    'tb_pedido_delivery',
                    'tb_item_pedido_delivery'
                  )
            """
        )
        tabelas = {row[0] for row in cursor.fetchall()}

        if {"tb_pedido", "tb_item_pedido"}.issubset(tabelas):
            return "tb_pedido", "tb_item_pedido"

        if {"tb_pedido_delivery", "tb_item_pedido_delivery"}.issubset(tabelas):
            return "tb_pedido_delivery", "tb_item_pedido_delivery"

        return None, None

    async def get_all_familias(self) -> List[dict]:
        """Retorna todas as famílias de produtos ativas."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    f.ID_FAMILIA,
                    f.DESCRICAO_FAMILIA
                FROM tb_familia_produto f
                ORDER BY f.DESCRICAO_FAMILIA
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()

            return [
                {
                    "ID_FAMILIA": row[0],
                    "DESCRICAO_FAMILIA": row[1],
                }
                for row in rows
            ]
        finally:
            conn.close()

    async def get_all_grades(self) -> List[dict]:
        """Retorna todas as grades de produtos (faixas de preço por quantidade)."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    g.ID_PRODUTO,
                    g.QTDE_INICIAL,
                    g.QTDE_FINAL,
                    g.PRECO_VENDA
                FROM tb_grade_produto g
                ORDER BY g.ID_PRODUTO, g.QTDE_INICIAL
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()

            return [
                {
                    "ID_PRODUTO": row[0],
                    "QTDE_INICIAL": row[1],
                    "QTDE_FINAL": row[2],
                    "PRECO_VENDA": float(row[3]) if isinstance(row[3], Decimal) else (row[3] or 0.0),
                }
                for row in rows
            ]
        finally:
            conn.close()

    def resolveImage(self, img: any):
        path = self.getStringBytesFromImage('img/nao1.jpg')

        if isinstance(img, bytes):
            path = self.getStringBytesFromImage(img)

        return path
    
    def getStringBytesFromImage(self, imageBytes):
        retorno = ''

        if isinstance(imageBytes, str):
            with open(imageBytes, 'rb') as f:
                retorno = base64.b64encode(f.read())
                f.close()

        elif isinstance(imageBytes, bytes):
            retorno = base64.b64encode(imageBytes)

        return str(retorno)[2:-1]