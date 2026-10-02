"""Rotas do laboratório. Só entram se ENABLE_LAB=true."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.lab import exigir_lab
from app.models.usuario import Usuario
from app.routers._erro import chamar
from app.schemas.lab import CenarioCriar, CenarioSaida, RespostasLabEntrada
from app.services.lab import (
    cenario_saida,
    executar_criacao,
    executar_exclusao,
    executar_respostas,
    listar_cenarios,
    obter_cenario,
    solicitar_cenario,
    solicitar_exclusao,
    solicitar_respostas,
)

router = APIRouter(prefix="/lab", tags=["lab"])


@router.get("/cenarios", response_model=list[CenarioSaida])
def get_cenarios(
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> list[CenarioSaida]:
    return [CenarioSaida(**cenario_saida(item)) for item in listar_cenarios(db, dono)]


@router.get("/cenarios/{cenario_id}", response_model=CenarioSaida)
def get_cenario(
    cenario_id: str,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> CenarioSaida:
    linha = chamar(lambda: obter_cenario(db, dono, cenario_id))
    return CenarioSaida(**cenario_saida(linha))


@router.post("/cenarios", response_model=CenarioSaida, status_code=202)
def post_cenario(
    corpo: CenarioCriar,
    background: BackgroundTasks,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> CenarioSaida:
    linha = chamar(
        lambda: solicitar_cenario(
            db,
            dono,
            corpo.nome,
            corpo.tipo,
            corpo.tamanho,
            corpo.perfil,
            corpo.seed,
            corpo.com_senha,
        )
    )
    background.add_task(executar_criacao, linha.id, corpo.com_senha)
    return CenarioSaida(**cenario_saida(linha))


@router.post(
    "/cenarios/{cenario_id}/respostas",
    response_model=CenarioSaida,
    status_code=202,
)
def post_respostas(
    cenario_id: str,
    corpo: RespostasLabEntrada,
    background: BackgroundTasks,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> CenarioSaida:
    linha = chamar(
        lambda: solicitar_respostas(
            db,
            dono,
            cenario_id,
            corpo.perfil,
            corpo.taxa,
            corpo.seed,
        )
    )
    seed = corpo.seed if corpo.seed is not None else linha.seed
    background.add_task(
        executar_respostas,
        linha.id,
        corpo.perfil,
        corpo.taxa,
        seed,
    )
    return CenarioSaida(**cenario_saida(linha))


@router.delete(
    "/cenarios/{cenario_id}",
    response_model=CenarioSaida,
    status_code=202,
)
def delete_cenario(
    cenario_id: str,
    confirmo: str,
    background: BackgroundTasks,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> CenarioSaida:
    linha = chamar(
        lambda: solicitar_exclusao(db, dono, cenario_id, confirmo)
    )
    background.add_task(executar_exclusao, linha.id, dono.id)
    return CenarioSaida(**cenario_saida(linha))


@router.get("/saude")
def saude_lab(_dono: Usuario = Depends(exigir_lab)) -> dict[str, str]:
    return {"status": "ok"}
