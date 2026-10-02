"""Apaga o que já venceu. Não mexe em sessão ativa nem em bloqueio vigente."""

import random
from datetime import datetime, timedelta

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import agora

_ultima: datetime | None = None
TRAVA = 727275


def _apagar(
    db: Session,
    tabela: str,
    onde: str,
    limite: datetime,
    lote: int,
    coluna: str = "id",
) -> int:
    total = 0
    while True:
        ids = (
            db.execute(
                text(f"select {coluna} from {tabela} where {onde} limit :lote"),
                {"limite": limite, "lote": lote},
            )
            .scalars()
            .all()
        )
        if not ids:
            break
        db.execute(
            text(f"delete from {tabela} where {coluna} in :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": list(ids)},
        )
        total += len(ids)
        if len(ids) < lote:
            break
    return total


def limpar_tabelas(db: Session, momento: datetime, lote: int = 500) -> dict[str, int]:
    regras = [
        (
            "sessoes",
            "(revogado_em is not null and revogado_em < :limite) "
            "or expira_em < :limite",
            momento - timedelta(days=2),
            "id",
        ),
        (
            "controle_acesso",
            "atualizado_em < :limite and "
            "(bloqueado_ate is null or bloqueado_ate < :limite)",
            momento - timedelta(days=1),
            "chave",
        ),
        (
            "tokens_redefinicao",
            "expira_em < :limite",
            momento - timedelta(days=7),
            "id",
        ),
        (
            "entregas_mensagem",
            "criado_em < :limite",
            momento - timedelta(days=90),
            "id",
        ),
        (
            "notificacoes",
            "lida_em is not null and lida_em < :limite",
            momento - timedelta(days=180),
            "id",
        ),
        (
            "logs_auditoria",
            "criado_em < :limite",
            momento - timedelta(days=settings.retencao_auditoria_dias),
            "id",
        ),
    ]
    return {
        tabela: _apagar(db, tabela, onde, limite, lote, coluna)
        for tabela, onde, limite, coluna in regras
    }


def tentar_limpar(
    db: Session,
    momento: datetime | None = None,
) -> dict[str, int] | None:
    global _ultima
    momento = momento or agora()
    if _ultima is not None and momento - _ultima < timedelta(hours=6):
        return None
    if random.random() > settings.manutencao_probabilidade:
        return None
    dialeto = db.get_bind().dialect.name
    if dialeto == "postgresql":
        livre = db.execute(text(f"select pg_try_advisory_lock({TRAVA})")).scalar()
        if not livre:
            return None
    try:
        saida = limpar_tabelas(db, momento)
        db.commit()
        _ultima = momento
        return saida
    finally:
        if dialeto == "postgresql":
            db.execute(text(f"select pg_advisory_unlock({TRAVA})"))
            db.commit()
