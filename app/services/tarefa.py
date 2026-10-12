"""Tarefas longas com job_id. Sem transação aberta durante o trabalho."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.models.base import agora
from app.models.tarefa import Tarefa
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth


def criar_tarefa(
    db: Session,
    dono: Usuario,
    tipo: str,
    projeto_id: str | None = None,
    total: int = 0,
) -> Tarefa:
    agora_ = agora()
    linha = Tarefa(
        id=novo_id(),
        dono_id=dono.id,
        projeto_id=projeto_id,
        tipo=tipo,
        status="PENDENTE",
        feito=0,
        total=total,
        falhas=0,
        erro=None,
        criado_em=agora_,
        atualizado_em=agora_,
        concluido_em=None,
    )
    db.add(linha)
    db.commit()
    db.refresh(linha)
    return linha


def concluir_tarefa(db: Session, tarefa: Tarefa, falhas: int = 0) -> Tarefa:
    tarefa.status = "CONCLUIDA" if falhas == 0 else "FALHOU"
    tarefa.falhas = falhas
    tarefa.feito = tarefa.total
    tarefa.concluido_em = agora()
    tarefa.atualizado_em = agora()
    db.commit()
    db.refresh(tarefa)
    return tarefa


def listar_tarefas(db: Session, dono: Usuario) -> list[Tarefa]:
    return list(
        db.scalars(
            select(Tarefa)
            .where(Tarefa.dono_id == dono.id)
            .order_by(Tarefa.criado_em.desc())
            .limit(50)
        ).all()
    )


def obter_tarefa(db: Session, dono: Usuario, tarefa_id: str) -> Tarefa:
    linha = db.get(Tarefa, tarefa_id)
    if linha is None or linha.dono_id != dono.id:
        raise ErroAuth(404, "Não encontrado.")
    return linha
