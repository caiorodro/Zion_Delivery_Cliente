import json
import logging
import os
from typing import List

from frontend.cfg.config import AppConfig
from frontend.base.server import ZionAPI
from frontend.models.listaProduto import ListaProduto
from frontend.models.familiaProduto import FamiliaProduto
from frontend.models.gradeProduto import GradeProduto


logger = logging.getLogger(__name__)


class CacheManager:
    """Gerencia cache local em JSON e mantém os dados em memória."""

    _produtos: List[ListaProduto] = []
    _familias: List[FamiliaProduto] = []
    _grades: List[GradeProduto] = []
    _loaded = False

    @classmethod
    def _ensure_dir(cls):
        os.makedirs("frontend/data", exist_ok=True)

    @classmethod
    def _save_json(cls, path: str, data: list):
        cls._ensure_dir()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    @classmethod
    def _load_json(cls, path: str) -> list:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    @classmethod
    def download_e_salvar(cls, cpf: str = "", telefone: str = "") -> bool:
        """Baixa dados da API e salva em JSON local, além de atualizar memória."""
        api = ZionAPI()
        try:
            produtos = api.download_produtos(cpf=cpf, telefone=telefone)
            familias = api.download_familias()
            grades = api.download_grades()

            if not produtos:
                return False

            cls._save_json(AppConfig.CACHE_PRODUTOS, produtos)
            cls._save_json(AppConfig.CACHE_FAMILIAS, familias)
            cls._save_json(AppConfig.CACHE_GRADES, grades)

            cls._produtos = [ListaProduto(**p) for p in produtos]
            cls._familias = [FamiliaProduto(**f) for f in familias]
            cls._grades = [GradeProduto(**g) for g in grades]
            cls._loaded = True
            return True
        except Exception as ex:
            logger.exception("Erro ao carregar dados da API para o cardapio")
            return False

    @classmethod
    def carregar_cache_local(cls) -> bool:
        """Carrega dados dos JSON locais para memória."""
        try:
            produtos = cls._load_json(AppConfig.CACHE_PRODUTOS)
            familias = cls._load_json(AppConfig.CACHE_FAMILIAS)
            grades = cls._load_json(AppConfig.CACHE_GRADES)

            if not produtos:
                return False

            cls._produtos = [ListaProduto(**p) for p in produtos]
            cls._familias = [FamiliaProduto(**f) for f in familias]
            cls._grades = [GradeProduto(**g) for g in grades]
            cls._loaded = True
            return True
        except Exception:
            logger.exception("Erro ao carregar cache local do cardapio")
            return False

    @classmethod
    def carregar_dados_api(cls) -> bool:
        """Compatibilidade: mantém nome antigo apontando para download + persistência local."""
        return cls.download_e_salvar()

    @classmethod
    def get_produtos(cls) -> List[ListaProduto]:
        return cls._produtos

    @classmethod
    def get_familias(cls) -> List[FamiliaProduto]:
        return cls._familias

    @classmethod
    def get_grades(cls) -> List[GradeProduto]:
        return cls._grades

    @classmethod
    def filtrar_produtos(cls, nome: str = "", id_familia: int = 0) -> List[ListaProduto]:
        result = cls._produtos
        
        if id_familia > 0:
            result = [p for p in result if p.ID_FAMILIA == id_familia]
        if nome.strip():
            termos = nome.strip().lower().split()
            for termo in termos:
                result = [p for p in result if termo in p.DESCRICAO_PRODUTO.lower()]
        return result

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded
