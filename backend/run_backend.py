import uvicorn
from cfg.config import Config

from multiprocessing import cpu_count, freeze_support

if __name__ == "__main__":
    freeze_support()
    _workers = int(cpu_count() * 0.75)

    uvicorn.run(
        "main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        log_level="info",
        workers=_workers
    )
