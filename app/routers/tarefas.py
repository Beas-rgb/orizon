"""Consulta de jobs. A execução pesada fica fora da transação do request."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.routers._erro import chamar
from app.services.tarefa import listar_tarefas, obter_tarefa

router = APIRouter(prefix="/tarefas", tags=["tarefas"])


class TarefaSaida(BaseModel):
    id: str
    tipo: str
    status: str
    feito: int
    total: int
    falhas: int
    projeto_id: str | None
    erro: str | None


def _saida(linha) -> TarefaSaida:
    return TarefaSaida(
        id=linha.id,
        tipo=linha.tipo,
        status=linha.status,
        feito=linha.feito,
        total=linha.total,
        falhas=linha.falhas,
        projeto_id=linha.projeto_id,
        erro=linha.erro,
    )


@router.get("", response_model=list[TarefaSaida])
def lista(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[TarefaSaida]:
    return [_saida(item) for item in listar_tarefas(db, usuario)]


@router.get("/{tarefa_id}", response_model=TarefaSaida)
def detalhe(
    tarefa_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> TarefaSaida:
    return _saida(chamar(lambda: obter_tarefa(db, usuario, tarefa_id)))


@router.get("/{tarefa_id}/arquivo")
def arquivo(
    tarefa_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    linha = chamar(lambda: obter_tarefa(db, usuario, tarefa_id))
    if linha.tipo != "EXPORTACAO" or not linha.resumo:
        raise HTTPException(status_code=404, detail="Não encontrado.")
    return Response(
        content=linha.resumo,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=equipe.csv"},
    )
