import json
import os
import time
from datetime import datetime
from typing import List, Optional

import requests

from frontend.cfg.config import AppConfig


class ZionAPI:
    """Cliente HTTP para comunicação com a API Zion Delivery."""

    def __init__(self):
        self.base_url = AppConfig.URL_API
        self.timeout = 15

    def _log(self, msg: str):
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {msg}")

    def _get(self, path: str, params: dict = None, retries: int = 3) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.ConnectionError:
                self._log(f"GET {url} – tentativa {attempt}/{retries} falhou (conexão)")
                if attempt < retries:
                    time.sleep(2)
            except requests.exceptions.Timeout:
                self._log(f"GET {url} – timeout na tentativa {attempt}/{retries}")
                if attempt < retries:
                    time.sleep(2)
            except requests.exceptions.HTTPError as e:
                self._log(f"GET {url} – erro HTTP {e.response.status_code}")
                raise
        return None

    def _post(self, path: str, data: dict, retries: int = 3) -> Optional[dict]:
        url = f"{self.base_url}{path}"
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(url, json=data, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.ConnectionError:
                self._log(f"POST {url} – tentativa {attempt}/{retries} falhou (conexão)")
                if attempt < retries:
                    time.sleep(2)
            except requests.exceptions.Timeout:
                self._log(f"POST {url} – timeout na tentativa {attempt}/{retries}")
                if attempt < retries:
                    time.sleep(2)
            except requests.exceptions.HTTPError as e:
                self._log(f"POST {url} – erro HTTP {e.response.status_code}")
                raise
        return None

    # ─── Produtos ───────────────────────────────────────────────

    def download_produtos(self) -> List[dict]:
        result = self._get("/produtos")
        return result if result is not None else []

    def download_familias(self) -> List[dict]:
        result = self._get("/familias")
        return result if result is not None else []

    def download_grades(self) -> List[dict]:
        result = self._get("/grades")
        return result if result is not None else []

    # ─── Endereços ──────────────────────────────────────────────

    def get_ufs(self) -> List[str]:
        result = self._get("/enderecos/ufs")
        return result if result is not None else []

    def get_cidades(self, uf: str) -> List[str]:
        result = self._get(f"/enderecos/cidades/{uf}")
        return result if result is not None else []

    def pesquisar_endereco(self, uf: str, cidade: str, termo: str) -> List[dict]:
        result = self._get("/enderecos/pesquisar", params={"uf": uf, "cidade": cidade, "termo": termo})
        return result if result is not None else []

    def buscar_por_cep(self, cep: str) -> List[dict]:
        result = self._get(f"/enderecos/cep/{cep}")
        return result if result is not None else []

    # ─── Frete ─────────────────────────────────────────────────

    def get_faixa_frete(self, distancia_km: float) -> Optional[dict]:
        return self._get("/fretes/faixa", params={"distancia_km": distancia_km})

    # ─── Pedidos ────────────────────────────────────────────────

    def criar_pedido(self, pedido_dict: dict) -> Optional[dict]:
        return self._post("/pedidos", pedido_dict)

    def get_status_pedido(self, numero_pedido: int) -> Optional[dict]:
        return self._get(f"/pedidos/{numero_pedido}/status")

    # ─── Health ─────────────────────────────────────────────────

    def health_check(self) -> bool:
        try:
            result = self._get("/health", retries=1)
            return result is not None
        except Exception:
            return False
