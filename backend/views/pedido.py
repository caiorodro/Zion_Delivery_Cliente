import datetime
from typing import Optional

from base.database import get_connection
from base.error_logger import append_exception_log
from base.qBase import qBase
from models.pedido import Pedido, StatusPedido


STATUS_DESCRICAO = {
    0: "Aguardando confirmação",
    1: "Pedido aceito",
    2: "Em preparo",
    3: "Saiu para entrega",
    4: "Entregue",
    99: "Cancelado",
}

class PedidoView:

    def __init__(self):
        self.qbase = qBase()

    def _default_value_by_type(self, data_type: str):
        numeric_types = {
            "tinyint", "smallint", "mediumint", "int", "bigint",
            "decimal", "float", "double", "bit",
        }
        text_types = {"char", "varchar", "text", "tinytext", "mediumtext", "longtext"}
        date_types = {"date", "datetime", "timestamp", "time", "year"}
        blob_types = {"blob", "tinyblob", "mediumblob", "longblob", "binary", "varbinary"}

        if data_type in numeric_types:
            return 0
        if data_type in text_types:
            return ""
        if data_type in date_types:
            return datetime.datetime.now()
        if data_type in blob_types:
            return None
        return ""

    def _get_columns_meta(self, cursor, table_name: str) -> list:
        cursor.execute(
            """
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    EXTRA
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """,
            (table_name,),
        )
        return cursor.fetchall()

    def _insert_dynamic_row(self, cursor, table_name: str, row_data: dict) -> int:
        """
        Insere uma linha usando o schema da tabela em runtime.
        - Ignora colunas auto_increment.
        - Usa valores do payload quando disponíveis.
        - Para colunas NOT NULL sem default não informadas, aplica valor padrão por tipo.
        """
        columns_meta = self._get_columns_meta(cursor, table_name)
        if not columns_meta:
            raise ValueError(f"Tabela {table_name} não encontrada")

        normalized_data = {str(k).upper(): v for k, v in row_data.items()}

        insert_columns = []
        insert_values = []

        for col_name, data_type, is_nullable, column_default, extra in columns_meta:
            col_key = str(col_name).upper()
            is_auto_increment = isinstance(extra, str) and "auto_increment" in extra.lower()
            if is_auto_increment:
                continue

            if col_key in normalized_data:
                insert_columns.append(col_name)
                insert_values.append(normalized_data[col_key])
                continue

            # Quando há default no banco, deixa o banco preencher.
            if column_default is not None:
                continue

            # Se permite nulo e não veio valor, grava nulo.
            if str(is_nullable).upper() == "YES":
                insert_columns.append(col_name)
                insert_values.append(None)
                continue

            # Último fallback para NOT NULL sem default.
            insert_columns.append(col_name)
            insert_values.append(self._default_value_by_type(str(data_type).lower()))

        if not insert_columns:
            raise ValueError(f"Nenhuma coluna disponível para inserir em {table_name}")

        placeholders = ", ".join(["%s"] * len(insert_columns))
        sql = f"INSERT INTO {table_name} ({', '.join(insert_columns)}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(insert_values))
        return int(cursor.lastrowid or 0)

    def _pick_existing_column(self, available_columns: set, candidates: list) -> Optional[str]:
        for col in candidates:
            if col in available_columns:
                return col
        return None

    def _normalize_document(self, value) -> str:
        if value is None:
            return ""
        raw = str(value).strip()
        if not raw:
            return ""
        digits = "".join(ch for ch in raw if ch.isdigit())
        return digits

    def _normalize_cep(self, value) -> str:
        if value is None:
            return ""
        raw = str(value).strip()
        if not raw:
            return ""
        return "".join(ch for ch in raw if ch.isdigit())

    def _get_or_create_cliente_id(self, cursor, pedido_data: dict) -> int:
        columns_meta = self._get_columns_meta(cursor, "tb_cliente")
        if not columns_meta:
            raise ValueError("Tabela tb_cliente não encontrada")

        colunas = {str(col[0]).upper() for col in columns_meta}

        id_col = self._pick_existing_column(colunas, ["ID_CLIENTE"])
        if not id_col:
            raise ValueError("Não foi possível identificar a chave de cliente em tb_cliente")

        cpf_col = self._pick_existing_column(colunas, ["CPF"])
        nome_col = self._pick_existing_column(colunas, ["NOME_CLIENTE", "NOME_FANTASIA_CLIENTE"])

        if not nome_col:
            raise ValueError("Não foi possível identificar a coluna de nome em tb_cliente")

        pedido_norm = {str(k).upper(): v for k, v in (pedido_data or {}).items()}

        cpf_raw = pedido_norm.get("CPF_CLIENTE")
        if cpf_raw in (None, ""):
            cpf_raw = pedido_norm.get("CPF")

        nome_cliente = str(pedido_norm.get("NOME_CLIENTE") or "").strip()
        cpf_cliente = self._normalize_document(cpf_raw)

        # Regra: busca por CPF quando informado; se vier em branco, busca por NOME_CLIENTE.
        if cpf_cliente and cpf_col:
            cursor.execute(
                f"""
                    SELECT {id_col}
                    FROM tb_cliente
                    WHERE REPLACE(REPLACE(REPLACE(TRIM({cpf_col}), '.', ''), '-', ''), '/', '') = %s
                    LIMIT 1
                """,
                (cpf_cliente,),
            )
            row = cursor.fetchone()
            if row:
                return int(row[0])
        else:
            if not nome_cliente:
                raise ValueError("NOME_CLIENTE é obrigatório quando CPF_CLIENTE não for informado")
            cursor.execute(
                f"""
                    SELECT {id_col}
                    FROM tb_cliente
                    WHERE UPPER(TRIM({nome_col})) = UPPER(TRIM(%s))
                    LIMIT 1
                """,
                (nome_cliente,),
            )
            row = cursor.fetchone()
            if row:
                return int(row[0])

        telefone_cliente = str(
            pedido_norm.get("TELEFONE_CLIENTE")
            or pedido_norm.get("TELEFONE")
            or ""
        ).strip()

        row_cliente = {
            "NOME_CLIENTE": nome_cliente,
            "NOME": nome_cliente,
            "CPF_CLIENTE": cpf_cliente,
            "CPF": cpf_cliente,
            "TELEFONE_CLIENTE": telefone_cliente,
            "TELEFONE": telefone_cliente,
        }

        id_cliente = self._insert_dynamic_row(cursor, "tb_cliente", row_cliente)

        if id_cliente > 0:
            return id_cliente

        # Fallback: caso o driver não retorne lastrowid, tenta localizar o recém-inserido.
        if cpf_cliente and cpf_col:
            cursor.execute(
                f"""
                    SELECT {id_col}
                    FROM tb_cliente
                    WHERE REPLACE(REPLACE(REPLACE(TRIM({cpf_col}), '.', ''), '-', ''), '/', '') = %s
                    ORDER BY {id_col} DESC
                    LIMIT 1
                """,
                (cpf_cliente,),
            )
        else:
            cursor.execute(
                f"""
                    SELECT {id_col}
                    FROM tb_cliente
                    WHERE UPPER(TRIM({nome_col})) = UPPER(TRIM(%s))
                    ORDER BY {id_col} DESC
                    LIMIT 1
                """,
                (nome_cliente,),
            )

        row = cursor.fetchone()
        if not row:
            raise ValueError("Não foi possível obter ID_CLIENTE em tb_cliente")
        return int(row[0])

    def _get_or_create_endereco_id(self, cursor, pedido_data: dict, id_cliente: int) -> int:
        columns_meta = self._get_columns_meta(cursor, "tb_endereco_cliente")
        if not columns_meta:
            raise ValueError("Tabela tb_endereco_cliente não encontrada")

        colunas = {str(col[0]).upper() for col in columns_meta}

        id_col = self._pick_existing_column(colunas, ["ID_ENDERECO", "ID_ENDERECO_CLIENTE", "ID"])
        if not id_col:
            raise ValueError("Não foi possível identificar a chave de endereço em tb_endereco_cliente")

        cep_col = self._pick_existing_column(colunas, ["CEP"])
        if not cep_col:
            raise ValueError("Não foi possível identificar a coluna CEP em tb_endereco_cliente")

        pedido_norm = {str(k).upper(): v for k, v in (pedido_data or {}).items()}

        cep_cliente = self._normalize_cep(pedido_norm.get("CEP"))

        if not cep_cliente:
            raise ValueError("CEP é obrigatório para localizar ou inserir endereço")

        # Regra: filtro de endereço pelo CEP.
        cursor.execute(
            f"""
                SELECT {id_col}
                FROM tb_endereco_cliente
                WHERE REPLACE(REPLACE(TRIM({cep_col}), '-', ''), '.', '') = %s
                ORDER BY {id_col} ASC
                LIMIT 1
            """,
            (cep_cliente,),
        )
        row = cursor.fetchone()
        if row:
            return int(row[0])

        endereco_cliente = str(pedido_norm.get("ENDERECO_CLIENTE") or "").strip()
        rua = str(pedido_norm.get("RUA") or endereco_cliente).strip()
        numero = str(pedido_norm.get("NUMERO") or "").strip()
        complemento = str(pedido_norm.get("COMPLEMENTO") or "").strip()
        bairro = str(
            pedido_norm.get("BAIRRO")
            or pedido_norm.get("BAIRRO_CLIENTE")
            or ""
        ).strip()
        cidade = str(pedido_norm.get("CIDADE") or "").strip()
        uf = str(pedido_norm.get("UF") or "").strip()

        row_endereco = {
            "ID_CLIENTE": id_cliente,
            "CEP": cep_cliente,
            "ENDERECO": rua,
            "RUA": rua,
            "LOGRADOURO": rua,
            "NUMERO": numero,
            "COMPLEMENTO": complemento,
            "BAIRRO": bairro,
            "CIDADE": cidade,
            "UF": uf,
        }

        id_endereco = self._insert_dynamic_row(cursor, "tb_endereco_cliente", row_endereco)
        if id_endereco > 0:
            return id_endereco

        # Fallback: caso o driver não retorne lastrowid, busca novamente por CEP.
        cursor.execute(
            f"""
                SELECT {id_col}
                FROM tb_endereco_cliente
                WHERE REPLACE(REPLACE(TRIM({cep_col}), '-', ''), '.', '') = %s
                ORDER BY {id_col} DESC
                LIMIT 1
            """,
            (cep_cliente,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Não foi possível obter ID_ENDERECO em tb_endereco_cliente")
        return int(row[0])

    def _get_consumidor_final_id(self, cursor) -> int:
        cursor.execute(
            """
                SELECT ID_CLIENTE
                FROM tb_cliente
                WHERE UPPER(TRIM(NOME_CLIENTE)) = 'CONSUMIDOR FINAL'
                LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Cliente 'CONSUMIDOR FINAL' não encontrado em tb_cliente")
        return int(row[0])

    def _get_endereco_cliente_id(self, cursor, id_cliente: int) -> int:
        columns_meta = self._get_columns_meta(cursor, "tb_endereco_cliente")
        if not columns_meta:
            raise ValueError("Tabela tb_endereco_cliente não encontrada")

        colunas = {str(col[0]).upper() for col in columns_meta}

        if "ID_ENDERECO" in colunas:
            id_col = "ID_ENDERECO"
        elif "ID_ENDERECO_CLIENTE" in colunas:
            id_col = "ID_ENDERECO_CLIENTE"
        else:
            raise ValueError("Não foi possível identificar a chave de endereço em tb_endereco_cliente")

        cursor.execute(
            f"""
                SELECT {id_col}
                FROM tb_endereco_cliente
                WHERE ID_CLIENTE = %s
                ORDER BY {id_col} ASC
                LIMIT 1
            """,
            (id_cliente,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Nenhum endereço encontrado em tb_endereco_cliente para ID_CLIENTE={id_cliente}")
        return int(row[0])

    def _try_get_caixa_id(self, cursor, where_sql: str, order_sql: str) -> Optional[int]:
        cursor.execute(
            f"""
                SELECT ac.ID_ABERTURA
                FROM tb_abertura_caixa ac
                {where_sql}
                {order_sql}
                LIMIT 1
            """
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None

    def _get_ultimo_caixa_id(self, cursor) -> int:
        cols_abertura = {str(col[0]).upper() for col in self._get_columns_meta(cursor, "tb_abertura_caixa")}
        cols_usuario = {str(col[0]).upper() for col in self._get_columns_meta(cursor, "tb_usuario")}

        ordem_coluna = "ac.ID_ABERTURA"

        for c in ["DATA_ABERTURA", "ID_ABERTURA"]:
            if c in cols_abertura:
                ordem_coluna = f"ac.{c}"
                break

        open_conditions = []
        for c in ["DATA_FECHAMENTO"]:
            if c in cols_abertura:
                open_conditions.append(f"ac.{c} IS NULL")

        if "DATA_FECHAMENTO" in cols_abertura:
            open_conditions.append("ac.DATA_FECHAMENTO IS NULL")

        open_sql = f"({' OR '.join(open_conditions)})" if open_conditions else "1=1"
        order_sql = f"ORDER BY {ordem_coluna} DESC"

        id_caixa = None

        # Preferência 1: caixa aberto de usuário delivery.
        if "ID_USUARIO" in cols_abertura and {"ID_USUARIO", "CAIXA_DELIVERY"}.issubset(cols_usuario):
            id_caixa = self._try_get_caixa_id(
                cursor,
                (
                    "INNER JOIN tb_usuario u ON u.ID_USUARIO = ac.ID_USUARIO "
                    f"WHERE COALESCE(u.CAIXA_DELIVERY, 0) = 1 AND {open_sql}"
                ),
                order_sql,
            )

            # Preferência 2: usuário delivery (mesmo sem flag explícita de aberto).
            if id_caixa is None:
                id_caixa = self._try_get_caixa_id(
                    cursor,
                    "INNER JOIN tb_usuario u ON u.ID_USUARIO = ac.ID_USUARIO WHERE COALESCE(u.CAIXA_DELIVERY, 0) = 1",
                    order_sql,
                )

        # Fallback 1: qualquer caixa aberto.
        if id_caixa is None:
            id_caixa = self._try_get_caixa_id(cursor, f"WHERE {open_sql}", order_sql)

        # Fallback 2: último caixa registrado.
        if id_caixa is None:
            id_caixa = self._try_get_caixa_id(cursor, "", order_sql)

        if id_caixa is None:
            raise ValueError("Nenhum registro encontrado em tb_abertura_caixa para determinar ID_CAIXA")

        return id_caixa

    def _get_primeiro_transporte_id(self, cursor) -> int:
        cursor.execute(
            """
                SELECT ID_TRANSPORTE
                FROM tb_transporte
                ORDER BY ID_TRANSPORTE ASC
                LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Nenhum registro encontrado em tb_transporte")
        return int(row[0])

    def _normalizar_data_autorizacao(self, value) -> str:
        """Converte DATA_AUTORIZACAO para formato YYYY-MM-DD quando possível."""
        if value is None:
            return "1901-01-01"

        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime("%Y-%m-%d")

        raw = str(value).strip().replace("'", "")
        if not raw:
            return "1901-01-01"

        # Já está em formato ISO de data.
        if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
            return raw[:10]

        formatos_entrada = [
            "%d/%m/%Y",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
        ]

        for fmt in formatos_entrada:
            try:
                return datetime.datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        return raw

    def gravar_pedido_robo(self, payload: dict) -> dict:
        """
        Recebe payload do robô e grava nas tabelas:
          - tb_pedido
          - tb_item_pedido
          - tb_pedido_pagamento
          - tb_fila_comanda
        """
        pedido_data = payload.get("pedido")
        itens_data = payload.get("itemsPedido")
        pagamento_data = payload.get("pagamento")
        impressao_data = payload.get("impressaoPedido") or {}

        if not isinstance(pedido_data, dict):
            raise ValueError("Campo 'pedido' é obrigatório e deve ser objeto")
        if not isinstance(itens_data, list) or len(itens_data) == 0:
            raise ValueError("Campo 'itemsPedido' é obrigatório e deve ter ao menos 1 item")
        if not isinstance(pagamento_data, list) or len(pagamento_data) == 0:
            raise ValueError("Campo 'pagamento' é obrigatório e deve ter ao menos 1 item")

        conn = get_connection()

        try:
            cursor = conn.cursor()

            pedido_data = dict(pedido_data)

            id_cliente = self._get_or_create_cliente_id(cursor, pedido_data)
            id_endereco = self._get_or_create_endereco_id(cursor, pedido_data, id_cliente)
            id_caixa = self._get_ultimo_caixa_id(cursor)
            id_transporte = self._get_primeiro_transporte_id(cursor)

            pedido_data["ID_CLIENTE"] = id_cliente
            pedido_data["ID_ENDERECO"] = id_endereco
            pedido_data["ID_CAIXA"] = id_caixa
            pedido_data["ID_TRANSPORTE"] = id_transporte

            numero_pedido = self._insert_dynamic_row(cursor, "tb_pedido", pedido_data)
            if numero_pedido <= 0:
                numero_pedido = int(pedido_data.get("NUMERO_PEDIDO", 0) or 0)
            if numero_pedido <= 0:
                raise ValueError("Não foi possível obter NUMERO_PEDIDO para vincular itens e pagamentos")

            for item in itens_data:
                if not isinstance(item, dict):
                    raise ValueError("Todos os itens de 'itemsPedido' devem ser objeto")
                row_item = dict(item)
                row_item["NUMERO_PEDIDO"] = numero_pedido
                self._insert_dynamic_row(cursor, "tb_item_pedido", row_item)

                row_atendimento = dict(row_item)
                row_atendimento["NUMERO_COMANDA"] = numero_pedido
                row_atendimento["PRECO"] = row_atendimento.get("PRECO_UNITARIO")
                row_atendimento["FECHADO"] = 1
                row_atendimento["DATA_HORA"] = datetime.datetime.now()
                row_atendimento["NUMERO_ENDERECO"] = str(
                    row_atendimento.get("NUMERO_ENDERECO") or ""
                )
                row_atendimento["COMPLEMENTO_ENDERECO"] = str(
                    row_atendimento.get("COMPLEMENTO_ENDERECO") or ""
                )
                self._insert_dynamic_row(cursor, "tb_atendimento_comanda", row_atendimento)

            for pg in pagamento_data:
                if not isinstance(pg, dict):
                    raise ValueError("Todos os itens de 'pagamento' devem ser objeto")

                row_pg = dict(pg)
                row_pg["NUMERO_PEDIDO"] = numero_pedido
                row_pg["ID_CAIXA"] = id_caixa

                if "DATA_AUTORIZACAO" in row_pg:
                    row_pg["DATA_AUTORIZACAO"] = self._normalizar_data_autorizacao(
                        row_pg.get("DATA_AUTORIZACAO")
                    )

                self._insert_dynamic_row(cursor, "tb_pedido_pagamento", row_pg)

            row_fila = dict(impressao_data)
            row_fila["NUMERO_PEDIDO"] = numero_pedido
            row_fila["NUMERO_COMANDA"] = numero_pedido
            row_fila["NUEMRO_COMANDA"] = numero_pedido
            row_fila["PROCESSADO"] = 0
            self._insert_dynamic_row(cursor, "tb_fila_comanda", row_fila)

            conn.commit()
            cursor.close()

            return {
                "NUMERO_PEDIDO": numero_pedido,
                "STATUS": "OK",
                "ID_CLIENTE": id_cliente,
                "ID_ENDERECO": id_endereco,
                "ID_CAIXA": id_caixa,
                "ID_TRANSPORTE": id_transporte,
                "ITENS_INSERIDOS": len(itens_data),
                "ATENDIMENTOS_COMANDA_INSERIDOS": len(itens_data),
                "PAGAMENTOS_INSERIDOS": len(pagamento_data),
            }
        except Exception as ex:
            append_exception_log("pedido.gravar_pedido_robo", ex)
            conn.rollback()
            raise ex
        finally:
            conn.close()

    def gravar_pedido(self, pedido: Pedido) -> dict:
        """Grava o pedido completo no banco de dados. Operação síncrona."""
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Insere cabeçalho do pedido
            sql_pedido = """
                INSERT INTO tb_pedido_delivery (
                    NOME_CLIENTE,
                    CPF_CLIENTE,
                    TELEFONE_CLIENTE,
                    RUA,
                    NUMERO,
                    COMPLEMENTO,
                    CEP,
                    BAIRRO,
                    CIDADE,
                    UF,
                    OBS_ENTREGADOR,
                    OBS_PEDIDO,
                    TAXA_ENTREGA,
                    TOTAL_PRODUTOS,
                    TOTAL_PEDIDO,
                    FORMA_PAGAMENTO,
                    TROCO_PARA,
                    STATUS_PEDIDO,
                    ORIGEM,
                    DATA_HORA
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            now = datetime.datetime.now()
            cursor.execute(sql_pedido, (
                pedido.DADOS_CLIENTE.NOME_CLIENTE,
                pedido.DADOS_CLIENTE.CPF,
                pedido.DADOS_CLIENTE.TELEFONE,
                pedido.ENDERECO_ENTREGA.RUA,
                pedido.ENDERECO_ENTREGA.NUMERO,
                pedido.ENDERECO_ENTREGA.COMPLEMENTO,
                pedido.ENDERECO_ENTREGA.CEP,
                pedido.ENDERECO_ENTREGA.BAIRRO,
                pedido.ENDERECO_ENTREGA.CIDADE,
                pedido.ENDERECO_ENTREGA.UF,
                pedido.ENDERECO_ENTREGA.OBS_ENTREGADOR,
                pedido.OBS_PEDIDO,
                pedido.TAXA_ENTREGA,
                pedido.TOTAL_PRODUTOS,
                pedido.TOTAL_PEDIDO,
                pedido.PAGAMENTO.FORMA_PAGAMENTO,
                pedido.PAGAMENTO.TROCO_PARA,
                0,  # STATUS_PEDIDO = Aguardando
                pedido.ORIGEM,
                now,
            ))

            numero_pedido = cursor.lastrowid

            # Insere itens do pedido
            sql_item = """
                INSERT INTO tb_item_pedido_delivery (
                    NUMERO_PEDIDO,
                    ID_PRODUTO,
                    DESCRICAO_PRODUTO,
                    ID_GRADE,
                    QTDE,
                    PRECO_UNITARIO,
                    TOTAL_ITEM,
                    OBS_ITEM
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            for item in pedido.ITEMS:
                cursor.execute(sql_item, (
                    numero_pedido,
                    item.ID_PRODUTO,
                    item.DESCRICAO_PRODUTO,
                    item.ID_GRADE,
                    item.QTDE,
                    item.PRECO_UNITARIO,
                    item.TOTAL_ITEM,
                    item.OBS_ITEM,
                ))

            conn.commit()
            cursor.close()

            return {"NUMERO_PEDIDO": numero_pedido, "STATUS": 0}

        except Exception as ex:
            append_exception_log("pedido.gravar_pedido", ex)
            conn.rollback()
            raise ex
        finally:
            conn.close()

    async def get_status_pedido(self, numero_pedido: int) -> dict:
        """Consulta o status do pedido. Operação assíncrona."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            sql = """
                SELECT
                    NUMERO_PEDIDO,
                    STATUS_PEDIDO,
                    DATA_HORA
                FROM tb_pedido_delivery
                WHERE NUMERO_PEDIDO = %s
            """
            cursor.execute(sql, (numero_pedido,))
            row = cursor.fetchone()
            cursor.close()

            if row is None:
                return {"NUMERO_PEDIDO": numero_pedido, "STATUS_PEDIDO": -1, "DESCRICAO_STATUS": "Pedido não encontrado", "DATA_HORA": ""}

            status_code = row[1]

            return {
                "NUMERO_PEDIDO": row[0],
                "STATUS_PEDIDO": status_code,
                "DESCRICAO_STATUS": STATUS_DESCRICAO.get(status_code, "Desconhecido"),
                "DATA_HORA": row[2].isoformat() if row[2] else "",
            }
        finally:
            conn.close()

    async def get_pedidos_pendentes(self) -> list:
        """Retorna todos os pedidos com STATUS_PEDIDO = 0, incluindo seus itens."""
        conn = get_connection()
        try:
            cursor = conn.cursor()

            sql_pedidos = """
                SELECT
                    NUMERO_PEDIDO,
                    NOME_CLIENTE,
                    CPF_CLIENTE,
                    TELEFONE_CLIENTE,
                    RUA,
                    NUMERO,
                    COMPLEMENTO,
                    CEP,
                    BAIRRO,
                    CIDADE,
                    UF,
                    OBS_ENTREGADOR,
                    OBS_PEDIDO,
                    TAXA_ENTREGA,
                    TOTAL_PRODUTOS,
                    TOTAL_PEDIDO,
                    FORMA_PAGAMENTO,
                    TROCO_PARA,
                    STATUS_PEDIDO,
                    ORIGEM,
                    DATA_HORA
                FROM tb_pedido_delivery
                WHERE STATUS_PEDIDO = 0
                ORDER BY DATA_HORA ASC
            """
            cursor.execute(sql_pedidos)
            pedidos_rows = cursor.fetchall()

            if not pedidos_rows:
                cursor.close()
                return []

            numeros_pedido = [row[0] for row in pedidos_rows]
            placeholders = ", ".join(["%s"] * len(numeros_pedido))

            sql_itens = f"""
                SELECT
                    NUMERO_PEDIDO,
                    ID_PRODUTO,
                    DESCRICAO_PRODUTO,
                    ID_GRADE,
                    QTDE,
                    PRECO_UNITARIO,
                    TOTAL_ITEM,
                    OBS_ITEM
                FROM tb_item_pedido_delivery
                WHERE NUMERO_PEDIDO IN ({placeholders})
            """
            cursor.execute(sql_itens, numeros_pedido)
            itens_rows = cursor.fetchall()
            cursor.close()

            # Agrupa itens por NUMERO_PEDIDO

            itens_por_pedido: dict = {}

            for item in itens_rows:
                num = item[0]
                if num not in itens_por_pedido:
                    itens_por_pedido[num] = []

                itens_por_pedido[num].append({
                    "ID_PRODUTO": item[1],
                    "DESCRICAO_PRODUTO": item[2],
                    "ID_GRADE": item[3],
                    "QTDE": item[4],
                    "PRECO_UNITARIO": float(item[5]),
                    "TOTAL_ITEM": float(item[6]),
                    "OBS_ITEM": item[7] or "",
                })

            result = []

            for row in pedidos_rows:
                numero_pedido = row[0]
                result.append({
                    "NUMERO_PEDIDO": numero_pedido,
                    "STATUS_PEDIDO": row[18],
                    "DESCRICAO_STATUS": STATUS_DESCRICAO.get(row[18], "Desconhecido"),
                    "DATA_HORA": row[20].isoformat() if row[20] else "",
                    "DADOS_CLIENTE": {
                        "NOME_CLIENTE": row[1],
                        "CPF": row[2] or "",
                        "TELEFONE": row[3] or "",
                    },
                    "ENDERECO_ENTREGA": {
                        "RUA": row[4],
                        "NUMERO": row[5],
                        "COMPLEMENTO": row[6] or "",
                        "CEP": row[7],
                        "BAIRRO": row[8],
                        "CIDADE": row[9],
                        "UF": row[10],
                        "OBS_ENTREGADOR": row[11] or "",
                    },
                    "OBS_PEDIDO": row[12] or "",
                    "TAXA_ENTREGA": float(row[13]),
                    "TOTAL_PRODUTOS": float(row[14]),
                    "TOTAL_PEDIDO": float(row[15]),
                    "PAGAMENTO": {
                        "FORMA_PAGAMENTO": row[16],
                        "TROCO_PARA": float(row[17]),
                    },
                    "ORIGEM": row[19] or "",
                    "ITEMS": itens_por_pedido.get(numero_pedido, [])
                })

            return result
        finally:
            conn.close()

    async def aceitar_pedido(self, numero_pedido: int) -> dict:
        """Atualiza STATUS_PEDIDO para 1 (Pedido aceito)."""
        conn = get_connection()

        try:
            cursor = conn.cursor()

            # Verifica se o pedido existe e está com STATUS_PEDIDO = 0
            cursor.execute(
                "SELECT STATUS_PEDIDO FROM tb_pedido_delivery WHERE NUMERO_PEDIDO = %s",
                (numero_pedido,)
            )

            row = cursor.fetchone()

            if row is None:
                cursor.close()
                return {"NUMERO_PEDIDO": numero_pedido, "STATUS_PEDIDO": -1, "DESCRICAO_STATUS": "Pedido não encontrado"}

            if row[0] != 0:
                cursor.close()
                status_code = row[0]

                return {
                    "NUMERO_PEDIDO": numero_pedido,
                    "STATUS_PEDIDO": status_code,
                    "DESCRICAO_STATUS": STATUS_DESCRICAO.get(status_code, "Desconhecido"),
                    "ATUALIZADO": False,
                    "DETALHE": "Pedido não está em status 'Aguardando confirmação'",
                }

            cursor.execute(
                "UPDATE tb_pedido_delivery SET STATUS_PEDIDO = 1 WHERE NUMERO_PEDIDO = %s",
                (numero_pedido,),
            )

            conn.commit()

            return {
                "NUMERO_PEDIDO": numero_pedido,
                "STATUS_PEDIDO": 1,
                "DESCRICAO_STATUS": STATUS_DESCRICAO[1],
                "ATUALIZADO": True
            }

        except Exception as ex:
            append_exception_log("pedido.aceitar_pedido", ex)
            conn.rollback()
            raise ex
        finally:
            conn.close()
