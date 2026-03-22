from typing import List
from base.database import get_connection
from base.qBase import qBase


class EnderecoView:

    def __init__(self):
        self.qbase = qBase()

    async def get_ufs(self) -> List[str]:
        """Retorna lista de UFs distintas da tabela enderecos."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            sql = "SELECT DISTINCT uf FROM enderecos ORDER BY uf"
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
            return [row[0] for row in rows if row[0]]
        finally:
            conn.close()

    async def get_cidades_por_uf(self, uf: str) -> List[str]:
        """Retorna cidades de uma UF específica."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            sql = "SELECT DISTINCT cidade FROM enderecos WHERE uf = %s ORDER BY cidade"
            cursor.execute(sql, (uf,))
            rows = cursor.fetchall()
            cursor.close()
            return [row[0] for row in rows if row[0]]
        finally:
            conn.close()

    async def pesquisar_endereco(self, uf: str, cidade: str, termo: str) -> List[dict]:
        """
        Pesquisa endereços filtrando por UF e Cidade primeiro.
        Aceita busca por CEP, logradouro ou bairro.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            termo_like = f"%{termo.strip()}%"

            sql = """
                SELECT
                    id        AS ID_LOGRADOURO,
                    cep       AS CEP,
                    logradouro AS LOGRADOURO,
                    bairro    AS BAIRRO,
                    cidade    AS CIDADE,
                    uf        AS UF,
                    latitude  AS LATITUDE,
                    longitude AS LONGITUDE
                FROM enderecos
                WHERE uf = %s
                  AND cidade = %s
                  AND ativo = 1
                  AND (
                        logradouro LIKE %s
                        OR cep LIKE %s
                        OR bairro LIKE %s
                  )
                ORDER BY logradouro
                LIMIT 50
            """
            cursor.execute(sql, (uf, cidade, termo_like, termo_like, termo_like))
            rows = cursor.fetchall()
            cursor.close()

            return [
                {
                    "ID_LOGRADOURO": row[0],
                    "CEP": row[1] or "",
                    "LOGRADOURO": row[2] or "",
                    "BAIRRO": row[3] or "",
                    "CIDADE": row[4] or "",
                    "UF": row[5] or "",
                    "LATITUDE": float(row[6]) if row[6] is not None else None,
                    "LONGITUDE": float(row[7]) if row[7] is not None else None,
                }
                for row in rows
            ]
        finally:
            conn.close()

    async def buscar_por_cep(self, cep: str) -> List[dict]:
        """Busca endereço diretamente pelo CEP."""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cep_clean = cep.replace("-", "").replace(".", "").strip()
            sql = """
                SELECT
                    id        AS ID_LOGRADOURO,
                    cep       AS CEP,
                    logradouro AS LOGRADOURO,
                    bairro    AS BAIRRO,
                    cidade    AS CIDADE,
                    uf        AS UF,
                    latitude  AS LATITUDE,
                    longitude AS LONGITUDE
                FROM enderecos
                WHERE REPLACE(cep, '-', '') = %s
                LIMIT 10
            """
            cursor.execute(sql, (cep_clean,))
            rows = cursor.fetchall()
            cursor.close()

            return [
                {
                    "ID_LOGRADOURO": row[0],
                    "CEP": row[1] or "",
                    "LOGRADOURO": row[2] or "",
                    "BAIRRO": row[3] or "",
                    "CIDADE": row[4] or "",
                    "UF": row[5] or "",
                    "LATITUDE": float(row[6]) if row[6] is not None else None,
                    "LONGITUDE": float(row[7]) if row[7] is not None else None,
                }
                for row in rows
            ]
        finally:
            conn.close()
