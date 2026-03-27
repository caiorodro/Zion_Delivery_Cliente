import base64
from typing import List
from decimal import Decimal

from base.database import get_connection
from base.qBase import qBase
from models.produto import Produto, ProdutoCreate
from models.familia_produto import FamiliaProduto
from models.grade_produto import GradeProduto

class ProdutoView:

    def __init__(self):
        self.qbase = qBase()

    def _get_preco_column(self, cursor) -> str:
        """Resolve a coluna de preco disponivel na tabela tb_produto."""
        cursor.execute(
            """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'tb_produto'
                  AND COLUMN_NAME IN ('PRECO_DELIVERY', 'PRECO_BALCAO')
                ORDER BY FIELD(COLUMN_NAME, 'PRECO_DELIVERY', 'PRECO_BALCAO')
                LIMIT 1
            """
        )
        row = cursor.fetchone()
        # Garante que não fique resultado pendente no cursor.
        cursor.fetchall()
        return row[0] if row else "PRECO_BALCAO"

    def _build_produto_dict(self, row) -> dict:
        return Produto(
            ID_PRODUTO=row[0],
            DESCRICAO_PRODUTO=row[1],
            PRECO_DELIVERY=float(row[2]) if isinstance(row[2], Decimal) else (row[2] or 0.0),
            PRODUTO_ATIVO=row[3],
            FOTO_PRODUTO=''
        ).__dict__


    def _default_value_by_type(self, data_type: str):
        numeric_types = {
            "tinyint", "smallint", "mediumint", "int", "bigint",
            "decimal", "float", "double", "bit",
        }
        blob_types = {"blob", "tinyblob", "mediumblob", "longblob", "binary", "varbinary"}

        if data_type in blob_types:
            return None
        if data_type in numeric_types:
            return 0
        return ""

    async def get_all_produtos(self) -> List[dict]:
        """Retorna todos os produtos ativos com preço delivery > 0."""
        
        conn = None

        try:
            conn = get_connection()
            cursor = conn.cursor()
            preco_column = self._get_preco_column(cursor)

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
                    p.{preco_column},
                    p.PRODUTO_ATIVO,
                    p.FOTO_PRODUTO
                FROM tb_produto p
            """.format(preco_column=preco_column)

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
                result.append(self._build_produto_dict(row))

            return result
        
        except Exception as ex:
            
            with open('/tmp/errorLog.txt', "a", encoding="utf-8") as log_file:
                log_file.write(f"Erro ao obter produtos: {str(ex)}\n")

            raise

        finally:
            try:
                conn.close()
            except:
                pass

    def update_produto(self, id_produto: int, body: dict) -> dict:
        """Atualiza um produto da tb_produto pelo ID_PRODUTO."""
        allowed_fields = {
            "DESCRICAO_PRODUTO",
            "PRECO_DELIVERY",
            "FOTO_PRODUTO",
            "PRODUTO_ATIVO",
        }

        payload = {key: value for key, value in body.items() if key in allowed_fields}

        if not payload:
            raise ValueError("Informe ao menos um dos campos permitidos para atualização")

        conn = get_connection()

        try:
            cursor = conn.cursor()
            preco_column = self._get_preco_column(cursor)

            cursor.execute(
                "SELECT COUNT(1) FROM tb_produto WHERE ID_PRODUTO = %s",
                (id_produto,),
            )

            exists = cursor.fetchone()

            if not exists or exists[0] == 0:
                return {}

            updates = []
            values = []

            if "DESCRICAO_PRODUTO" in payload:
                descricao = str(payload["DESCRICAO_PRODUTO"]).strip()
                if not descricao:
                    raise ValueError("DESCRICAO_PRODUTO não pode ser vazia")
                updates.append("DESCRICAO_PRODUTO = %s")
                values.append(descricao)

            if "PRECO_DELIVERY" in payload:
                try:
                    preco = float(payload["PRECO_DELIVERY"])
                except (TypeError, ValueError):
                    raise ValueError("PRECO_DELIVERY deve ser numérico")
                if preco < 0:
                    raise ValueError("PRECO_DELIVERY deve ser maior ou igual a zero")
                updates.append(f"{preco_column} = %s")
                values.append(preco)

            if "FOTO_PRODUTO" in payload:
                foto_produto = payload["FOTO_PRODUTO"]
                if foto_produto in (None, ""):
                    updates.append("FOTO_PRODUTO = %s")
                    values.append(None)
                else:
                    try:
                        foto_bytes = base64.b64decode(str(foto_produto).strip(), validate=True)
                    except Exception as ex:
                        raise ValueError("FOTO_PRODUTO deve estar em base64 válido") from ex
                    updates.append("FOTO_PRODUTO = %s")
                    values.append(foto_bytes)

            if "PRODUTO_ATIVO" in payload:
                try:
                    produto_ativo = int(payload["PRODUTO_ATIVO"])
                except (TypeError, ValueError):
                    raise ValueError("PRODUTO_ATIVO deve ser 0 ou 1")
                if produto_ativo not in (0, 1):
                    raise ValueError("PRODUTO_ATIVO deve ser 0 ou 1")
                updates.append("PRODUTO_ATIVO = %s")
                values.append(produto_ativo)

            sql = f"UPDATE tb_produto SET {', '.join(updates)} WHERE ID_PRODUTO = %s"
            values.append(id_produto)
            cursor.execute(sql, tuple(values))
            conn.commit()

            select_sql = f"""
                SELECT
                    ID_PRODUTO,
                    DESCRICAO_PRODUTO,
                    {preco_column},
                    PRODUTO_ATIVO,
                    FOTO_PRODUTO
                FROM tb_produto
                WHERE ID_PRODUTO = %s
            """
            cursor.execute(select_sql, (id_produto,))
            row = cursor.fetchone()
            cursor.close()

            return self._build_produto_dict(row) if row else {}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_produto(self, produto: ProdutoCreate) -> dict:
        """Insere um novo registro em tb_produto com defaults para campos não informados."""
        conn = get_connection()

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                    SELECT
                        COLUMN_NAME,
                        DATA_TYPE,
                        COLUMN_KEY,
                        EXTRA
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'tb_produto'
                    ORDER BY ORDINAL_POSITION
                """
            )
            columns_meta = cursor.fetchall()

            if not columns_meta:
                raise ValueError("Tabela tb_produto não encontrada")

            required_values = {
                "CODIGO_PRODUTO": str(produto.CODIGO_PRODUTO).strip(),
                "CODIGO_PRODUTO_PDV": str(produto.CODIGO_PRODUTO_PDV).strip(),
                "DESCRICAO_PRODUTO": str(produto.DESCRICAO_PRODUTO).strip(),
                "PRECO_BALCAO": float(produto.PRECO_BALCAO),
                "PRECO_DELIVERY": float(produto.PRECO_DELIVERY),
                "ID_TRIBUTO": int(produto.ID_TRIBUTO),
                "ID_FAMILIA": int(produto.ID_FAMILIA),
                "ID_EMPRESA": int(produto.ID_EMPRESA),
                "PRODUTO_ATIVO": int(produto.PRODUTO_ATIVO)
            }

            if not required_values["DESCRICAO_PRODUTO"]:
                raise ValueError("DESCRICAO_PRODUTO não pode ser vazia")

            insert_columns = []
            insert_values = []

            for col_name, data_type, _col_key, extra in columns_meta:
                is_auto_increment = isinstance(extra, str) and "auto_increment" in extra.lower()
                if is_auto_increment:
                    continue

                insert_columns.append(col_name)

                if col_name in required_values:
                    insert_values.append(required_values[col_name])
                else:
                    insert_values.append(self._default_value_by_type(str(data_type).lower()))

            placeholders = ", ".join(["%s"] * len(insert_columns))
            sql = f"INSERT INTO tb_produto ({', '.join(insert_columns)}) VALUES ({placeholders})"
            cursor.execute(sql, tuple(insert_values))
            conn.commit()

            novo_id = cursor.lastrowid
            cursor.close()

            return {
                "ID_PRODUTO": novo_id,
                "CODIGO_PRODUTO": required_values["CODIGO_PRODUTO"],
                "CODIGO_PRODUTO_PDV": required_values["CODIGO_PRODUTO_PDV"],
                "DESCRICAO_PRODUTO": required_values["DESCRICAO_PRODUTO"],
                "PRECO_BALCAO": required_values["PRECO_BALCAO"],
                "PRECO_DELIVERY": required_values["PRECO_DELIVERY"],
                "ID_TRIBUTO": required_values["ID_TRIBUTO"],
                "ID_FAMILIA": required_values["ID_FAMILIA"],
                "ID_EMPRESA": required_values["ID_EMPRESA"],
                "PRODUTO_ATIVO": required_values["PRODUTO_ATIVO"],
            }
        except Exception:
            conn.rollback()
            raise
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