"""Tokens opacos e JWT.

O token que vai no e-mail é aleatório. No banco fica só o hash SHA-256.
Quem copiar a tabela não reutiliza o link. O JWT de acesso é curto;
o refresh fica na tabela sessoes, também só como hash.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

ALGORITMO = "HS256"


def novo_token_opaco() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _agora() -> datetime:
    return datetime.now(UTC)


def criar_access_token(usuario_id: str, papel: str) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET não configurado")
    expira = _agora() + timedelta(minutes=settings.jwt_access_minutos)
    return jwt.encode(
        {"sub": usuario_id, "papel": papel, "typ": "access", "exp": expira},
        settings.jwt_secret,
        algorithm=ALGORITMO,
    )


def criar_refresh_token(usuario_id: str) -> tuple[str, str, datetime]:
    """Devolve (token cru, hash, expiração). Só o hash vai para o banco."""
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET não configurado")
    cru = secrets.token_urlsafe(32)
    expira = _agora() + timedelta(days=settings.jwt_refresh_dias)
    return cru, hash_token(cru), expira


def ler_access_token(token: str) -> dict[str, str]:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET não configurado")
    try:
        dados = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITMO])
    except JWTError as exc:
        raise ValueError("token inválido") from exc
    if dados.get("typ") != "access" or not dados.get("sub"):
        raise ValueError("token inválido")
    return {"sub": str(dados["sub"]), "papel": str(dados.get("papel", ""))}


def novo_id() -> str:
    return str(uuid.uuid4())
