from typing import Dict

from base.database import get_connection


class EmpresaView:

    def get_dados_splash(self) -> Dict[str, str]:
        """Retorna os dados básicos da empresa para a splash screen."""
        conn = None
        cursor = None

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                    SELECT
                        ID_EMPRESA,
                        NOME_FANTASIA
                    FROM tb_empresa
                    ORDER BY ID_EMPRESA
                    LIMIT 1
                """
            )
            row = cursor.fetchone()

            if not row:
                return {"NOME_FANTASIA": "Zion"}

            nome_fantasia = str(row[1] or "").strip() or "Zion"
            return {
                "ID_EMPRESA": int(row[0]),
                "NOME_FANTASIA": nome_fantasia,
            }
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass

            try:
                if conn:
                    conn.close()
            except Exception:
                pass
