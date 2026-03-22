from typing import Optional

from base.database import get_connection


class FreteView:
    """Consultas de frete por faixa de distância na tabela tb_frete."""

    _CANDIDATOS_INICIAL = [
        "distancia_inicial", "km_inicial", "km_inicio", "inicio_km", "faixa_inicial", "distancia_de"
    ]
    _CANDIDATOS_FINAL = [
        "distancia_final", "km_final", "km_fim", "fim_km", "faixa_final", "distancia_ate", "distancia"
    ]
    _CANDIDATOS_VALOR = [
        "valor_frete", "valor_entrega", "valor", "taxa_entrega", "taxa", "preco"
    ]
    _CANDIDATOS_ATIVO = [
        "ativo", "fl_ativo", "status"
    ]

    def _pick_coluna(self, cols_map: dict, candidatos: list) -> Optional[str]:
        for nome in candidatos:
            if nome in cols_map:
                return cols_map[nome]
        return None

    async def get_faixa_por_distancia(self, distancia_km: float) -> Optional[dict]:
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("SHOW TABLES LIKE 'tb_frete'")
            if cursor.fetchone() is None:
                cursor.close()
                return None

            cursor.execute("SHOW COLUMNS FROM tb_frete")
            columns = cursor.fetchall()
            cols_map = {str(row[0]).lower(): str(row[0]) for row in columns}

            col_inicial = self._pick_coluna(cols_map, self._CANDIDATOS_INICIAL)
            col_final = self._pick_coluna(cols_map, self._CANDIDATOS_FINAL)
            col_valor = self._pick_coluna(cols_map, self._CANDIDATOS_VALOR)
            col_ativo = self._pick_coluna(cols_map, self._CANDIDATOS_ATIVO)

            if col_valor is None or col_final is None:
                cursor.close()
                return None

            inicial_expr = f"`{col_inicial}`" if col_inicial else "0"
            final_expr = f"`{col_final}`"
            valor_expr = f"`{col_valor}`"

            where_parts = ["%s >= COALESCE(" + inicial_expr + ", 0)", "%s <= COALESCE(" + final_expr + ", 999999)"]
            params = [distancia_km, distancia_km]

            if col_ativo:
                where_parts.append(f"COALESCE(`{col_ativo}`, 1) = 1")

            sql = f"""
                SELECT
                    COALESCE({inicial_expr}, 0) AS KM_INICIAL,
                    COALESCE({final_expr}, 999999) AS KM_FINAL,
                    COALESCE({valor_expr}, 0) AS VALOR_FRETE
                FROM tb_frete
                WHERE {' AND '.join(where_parts)}
                ORDER BY COALESCE({inicial_expr}, 0) DESC
                LIMIT 1
            """

            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return {
                "KM_INICIAL": float(row[0]) if row[0] is not None else 0.0,
                "KM_FINAL": float(row[1]) if row[1] is not None else 0.0,
                "VALOR_FRETE": float(row[2]) if row[2] is not None else 0.0,
            }
        finally:
            conn.close()
