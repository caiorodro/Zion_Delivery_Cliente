import datetime
import json
from decimal import Decimal

class qBase:

    def treat_row(self, row: tuple) -> list:
        result = list(row)
        for i, item in enumerate(result):
            if isinstance(item, Decimal):
                result[i] = float(item)
            elif isinstance(item, str):
                result[i] = item.replace('\u201c', '"').replace('\u201d', '"')
            elif isinstance(item, (datetime.date, datetime.datetime)):
                result[i] = item.isoformat()
        return result

    def rows_to_list(self, rows: list) -> list:
        return [self.treat_row(row) for row in rows]

    def to_json(self, rows: list) -> str:
        return json.dumps(self.rows_to_list(rows))

    def format_date(self, dt=None) -> str:
        if dt is None:
            dt = datetime.datetime.today()
        return dt.strftime("%d/%m/%Y")

    def format_datetime(self, dt=None) -> str:
        if dt is None:
            dt = datetime.datetime.today()
        return dt.strftime("%d/%m/%Y %H:%M")
