"""Rotas do laboratório. Só entram se ENABLE_LAB=true."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.lab import exigir_lab
from app.models.usuario import Usuario
from app.routers._erro import chamar
from app.schemas.lab import (
    CenarioCriar,
    CenarioSaida,
    ConviteLabEntrada,
    RespostasLabEntrada,
)
from app.services.lab import (
    cenario_saida,
    emitir_tokens_carga,
    executar_criacao,
    executar_exclusao,
    executar_respostas,
    listar_cenarios,
    obter_cenario,
    solicitar_cenario,
    solicitar_exclusao,
    solicitar_respostas,
)
from app.services.lab.acesso import convidar_no_cenario, entrar_como_orgao
from app.services.lab.exclusao import prever_exclusao

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


@router.post("/cenarios/{cenario_id}/tokens")
def post_tokens(
    cenario_id: str,
    quantidade: int,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    return chamar(
        lambda: emitir_tokens_carga(db, dono, cenario_id, quantidade)
    )


@router.get("/saude")
def saude_lab(_dono: Usuario = Depends(exigir_lab)) -> dict[str, str]:
    return {"status": "ok"}


@router.get("/limites")
def limites_lab(_dono: Usuario = Depends(exigir_lab)) -> dict[str, int | bool]:
    return {
        "max_participantes": settings.lab_max_participantes,
        "limite_banco_mb": settings.lab_limite_banco_mb,
        "tokens_permitidos": settings.lab_tokens_permitidos,
        "tamanho_min": 10,
        "tamanho_max": 600,
    }


@router.get("/cenarios/{cenario_id}/exclusao-previa")
def exclusao_previa(
    cenario_id: str,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> dict:
    return chamar(lambda: prever_exclusao(db, dono, cenario_id))


@router.post("/cenarios/{cenario_id}/entrar-como-orgao")
def post_orgao(
    cenario_id: str,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> dict:
    return chamar(lambda: entrar_como_orgao(db, dono, cenario_id))


@router.post("/cenarios/{cenario_id}/convites")
def post_convite(
    cenario_id: str,
    corpo: ConviteLabEntrada,
    dono: Usuario = Depends(exigir_lab),
    db: Session = Depends(get_db),
) -> dict:
    return chamar(
        lambda: convidar_no_cenario(
            db,
            dono,
            cenario_id,
            corpo.nome,
            corpo.email,
            corpo.papel,
            corpo.modo,
            corpo.autorizo_envio,
        )
    )
