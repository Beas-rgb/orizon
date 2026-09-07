from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tokens import ler_access_token
from app.models.usuario import Usuario

_bearer = HTTPBearer(auto_error=False)


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
    usuario = db.get(Usuario, dados["sub"])
    if usuario is None or usuario.deleted_at is not None or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return usuario
