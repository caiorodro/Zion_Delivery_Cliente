import datetime
from typing import Optional

from base.database import get_connection
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
            conn.rollback()
            raise ex
        finally:
            conn.close()
