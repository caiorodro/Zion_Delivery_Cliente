import jwt
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from werkzeug.security import generate_password_hash, check_password_hash

from cfg.config import Config
from base.error_logger import append_exception_log


class Authentication:

    PALAVRA_PASSE = "zionDelivery2026"

    @staticmethod
    def generate_token() -> str:
        passe = generate_password_hash(Authentication.PALAVRA_PASSE)

        if not check_password_hash(passe, Authentication.PALAVRA_PASSE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Credenciais inválidas para autenticação",
            )

        token = Authentication.encode_token(passe)
        return token

    @staticmethod
    def encode_token(subject) -> str:
        try:
            payload = {
                "exp": datetime.now() + timedelta(days=2),
                "iat": datetime.now(),
                "sub": str(subject),
            }
            return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")
        except Exception:
            append_exception_log("authentication.encode_token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha na criação do token de autenticação",
            )

    @staticmethod
    def decode_token(token: str):
        try:
            b1 = bytes(token, encoding="raw_unicode_escape")
            payload = jwt.decode(b1, Config.SECRET_KEY, algorithms=["HS256"])
            return payload["sub"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token expirado",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token inválido",
            )

    @staticmethod
    def verify_token(token: str):
        Authentication.decode_token(token)
