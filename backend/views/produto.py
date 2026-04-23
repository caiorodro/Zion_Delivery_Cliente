import base64
from typing import List
from decimal import Decimal

from base.database import get_connection
from base.error_logger import append_exception_log
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
        foto_produto = ""
        foto_raw = row[5] if len(row) > 5 else None

        if isinstance(foto_raw, (bytes, bytearray)) and foto_raw:
            foto_produto = base64.b64encode(foto_raw).decode("utf-8")
        elif isinstance(foto_raw, str) and foto_raw.strip():
            foto_produto = foto_raw.strip()

        codigo_wabiz = str(row[6]) if len(row) > 6 and row[6] else ""

        return Produto(
            ID_PRODUTO=row[0],
            DESCRICAO_PRODUTO=row[2],
            PRECO_DELIVERY=float(row[3]) if isinstance(row[3], Decimal) else (row[3] or 0.0),
            PRODUTO_ATIVO=row[4],
            FOTO_PRODUTO=foto_produto,
            CODIGO_WABIZ=codigo_wabiz
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

    def _normalize_digits(self, value: str) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    async def get_all_produtos(self, cpf: str = "", telefone: str = "") -> List[dict]:
        """Retorna produtos ativos priorizando o último pedido do cliente e os mais vendidos nos últimos 15 dias."""

        conn = None

        try:
            conn = get_connection()
            cursor = conn.cursor()
            preco_column = self._get_preco_column(cursor)
            tabela_pedido, tabela_item = self._resolver_tabelas_historico(cursor)

            cpf_digits = self._normalize_digits(cpf)
            telefone_digits = self._normalize_digits(telefone)

            sql = """
                SELECT
                    p.ID_PRODUTO,
                    p.ID_FAMILIA,
                    p.DESCRICAO_PRODUTO,
                    p.{preco_column},
                    p.PRODUTO_ATIVO,
                    p.FOTO_PRODUTO,
                    p.CODIGO_WABIZ
                FROM tb_produto p
            """.format(preco_column=preco_column)

            params = []
            order_parts = []

            if tabela_pedido and tabela_item:
                sql += f"""
                    LEFT JOIN (
                        SELECT
                            ip.ID_PRODUTO,
                            SUM(COALESCE(ip.QTDE, 0)) AS QTDE_VENDIDA_15D
                        FROM {tabela_item} ip
                        INNER JOIN {tabela_pedido} ped
                            ON ped.NUMERO_PEDIDO = ip.NUMERO_PEDIDO
                        WHERE ped.DATA_HORA >= (NOW() - INTERVAL 15 DAY)
                          AND COALESCE(ped.STATUS_PEDIDO, 0) <> 99
                        GROUP BY ip.ID_PRODUTO
                    ) h15 ON h15.ID_PRODUTO = p.ID_PRODUTO
                """

                filtros_cliente = []
                if telefone_digits:
                    filtros_cliente.append(
                        "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(ped2.TELEFONE_CLIENTE, ''), '(', ''), ')', ''), '-', ''), ' ', ''), '+', '') = %s"
                    )
                    params.append(telefone_digits)

                if cpf_digits:
                    filtros_cliente.append(
                        "REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(ped2.CPF_CLIENTE, ''), '.', ''), '-', ''), ' ', ''), '/', '') = %s"
                    )
                    params.append(cpf_digits)

                if filtros_cliente:
                    filtro_cliente_sql = " OR ".join(filtros_cliente)
                    sql += f"""
                        LEFT JOIN (
                            SELECT
                                ult.ID_PRODUTO,
                                MIN(ult.ORDEM_ITEM) AS POSICAO_ULTIMO_PEDIDO
                            FROM (
                                SELECT
                                    ip.ID_PRODUTO,
                                    ip.ID_ITEM AS ORDEM_ITEM
                                FROM {tabela_item} ip
                                INNER JOIN (
                                    SELECT ped2.NUMERO_PEDIDO
                                    FROM {tabela_pedido} ped2
                                    WHERE COALESCE(ped2.STATUS_PEDIDO, 0) <> 99
                                      AND ({filtro_cliente_sql})
                                    ORDER BY ped2.DATA_HORA DESC, ped2.NUMERO_PEDIDO DESC
                                    LIMIT 1
                                ) ult_ped
                                    ON ult_ped.NUMERO_PEDIDO = ip.NUMERO_PEDIDO
                            ) ult
                            GROUP BY ult.ID_PRODUTO
                        ) cli ON cli.ID_PRODUTO = p.ID_PRODUTO
                    """
                    order_parts.extend([
                        "CASE WHEN cli.POSICAO_ULTIMO_PEDIDO IS NULL THEN 1 ELSE 0 END",
                        "cli.POSICAO_ULTIMO_PEDIDO ASC",
                    ])

                order_parts.append("COALESCE(h15.QTDE_VENDIDA_15D, 0) DESC")
            else:
                order_parts.append("p.DESCRICAO_PRODUTO ASC")

            sql += " WHERE p.PRODUTO_ATIVO = 1"

            if not order_parts or order_parts[-1] != "p.DESCRICAO_PRODUTO ASC":
                order_parts.append("p.DESCRICAO_PRODUTO ASC")

            sql += " ORDER BY " + ", ".join(order_parts)

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            cursor.close()

            return [self._build_produto_dict(row) for row in rows]

        except Exception as ex:
            append_exception_log("produto.get_all_produtos", ex)
            raise

        finally:
            try:
                conn.close()
            except:
                pass

    def update_produto(self, codigo_wabiz: str, body: dict) -> dict:
        """Atualiza um produto da tb_produto pelo CODIGO_WABIZ."""
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
                "SELECT COUNT(1) FROM tb_produto WHERE CODIGO_WABIZ = %s",
                (codigo_wabiz,),
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

            sql = f"UPDATE tb_produto SET {', '.join(updates)} WHERE CODIGO_WABIZ = %s"
            values.append(codigo_wabiz)
            cursor.execute(sql, tuple(values))
            conn.commit()

            select_sql = f"""
                SELECT
                    ID_PRODUTO,
                    ID_PRODUTO,
                    DESCRICAO_PRODUTO,
                    {preco_column},
                    PRODUTO_ATIVO,
                    FOTO_PRODUTO,
                    CODIGO_WABIZ
                FROM tb_produto
                WHERE CODIGO_WABIZ = %s
            """
            cursor.execute(select_sql, (codigo_wabiz,))
            row = cursor.fetchone()
            cursor.close()

            return self._build_produto_dict(row) if row else {}
        except Exception as ex:
            append_exception_log("produto.update_produto", ex)
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
                "PRODUTO_ATIVO": int(produto.PRODUTO_ATIVO),
                "CODIGO_WABIZ": str(produto.CODIGO_WABIZ).strip()
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
                "CODIGO_WABIZ": required_values["CODIGO_WABIZ"]
            }
        except Exception as ex:
            append_exception_log("produto.create_produto", ex)
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

        if {"tb_pedido_delivery", "tb_item_pedido_delivery"}.issubset(tabelas):
            return "tb_pedido_delivery", "tb_item_pedido_delivery"

        if {"tb_pedido", "tb_item_pedido"}.issubset(tabelas):
            return "tb_pedido", "tb_item_pedido"

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