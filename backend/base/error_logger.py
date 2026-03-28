import os
import traceback
from datetime import datetime
from typing import Optional


ERROR_LOG_PATH = "/tmp/errorLog.txt"


def append_exception_log(context: str, ex: Optional[Exception] = None):
    """Registra exceções em /tmp/errorLog.txt com append, data/hora e traceback."""
    try:
        os.makedirs("/tmp", exist_ok=True)

        trace = traceback.format_exc()
        if trace.strip() == "NoneType: None":
            if ex is not None:
                trace = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
            else:
                trace = "Traceback indisponível (fora de bloco except)."

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(
                f"[{now}] {context}\n"
                f"{trace}\n"
                "-" * 100
                + "\n"
            )
    except Exception:
        # Evita propagar erro de logging e mascarar exceção original.
        pass
