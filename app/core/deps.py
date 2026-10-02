from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tokens import ler_access_token
from app.models.sessao import Sessao
from app.models.usuario import Usuario

_bearer = HTTPBearer(auto_error=False)


def _expirada(sessao: Sessao, agora: datetime) -> bool:
    expira = sessao.expira_em
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=UTC)
    return expira <= agora


def usuario_atual(
    credencial: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credencial is None or credencial.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Não autenticado.")
    try:
        dados = ler_access_token(credencial.credentials)
    except (ValueError, RuntimeError):
        raise HTTPException(status_code=401, detail="Não autenticado.") from None
    agora = datetime.now(UTC)
    par = db.execute(
        select(Sessao, Usuario)
        .join(Usuario, Usuario.id == Sessao.usuario_id)
        .where(
            Sessao.id == dados["sid"],
            Sessao.usuario_id == dados["sub"],
        )
    ).first()
    if par is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    sessao, usuario = par
    if (
        sessao.revogado_em is not None
        or _expirada(sessao, agora)
        or usuario.deleted_at is not None
        or not usuario.ativo
    ):
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return usuario
