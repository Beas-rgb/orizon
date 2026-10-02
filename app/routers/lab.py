"""Rotas do laboratório. Só entram se ENABLE_LAB=true."""

from fastapi import APIRouter, Depends

from app.core.lab import exigir_lab
from app.models.usuario import Usuario
from app.schemas.lab import CenarioSaida

router = APIRouter(prefix="/lab", tags=["lab"])


@router.get("/cenarios", response_model=list[CenarioSaida])
def listar_cenarios(
    _dono: Usuario = Depends(exigir_lab),
) -> list[CenarioSaida]:
    """Lista vazia até a T5.3. A guarda já está ativa."""
    return []


@router.get("/saude")
def saude_lab(_dono: Usuario = Depends(exigir_lab)) -> dict[str, str]:
    return {"status": "ok"}
