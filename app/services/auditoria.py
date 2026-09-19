"""Registro único de auditoria. Sem dados sensíveis no `acao`."""

from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.models.auditoria import LogAuditoria
from app.models.base import agora


def registrar(db: Session, acao: str, usuario_id: str | None) -> None:
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=usuario_id,
            acao=acao,
            criado_em=agora(),
        )
    )
