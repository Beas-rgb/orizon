"""Guarda do laboratório. Falha sempre em 404 — não revela a existência."""

from fastapi import Depends, HTTPException

from app.core.config import settings
from app.core.deps import usuario_atual
from app.models.usuario import Usuario

MSG_404 = "Não encontrado."


def exigir_lab(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    """Só CONSULTOR com tipo_conta=TESTE e ENABLE_LAB. Senão 404."""
    if not settings.enable_lab:
        raise HTTPException(status_code=404, detail=MSG_404)
    if usuario.papel != "CONSULTOR":
        raise HTTPException(status_code=404, detail=MSG_404)
    if getattr(usuario, "tipo_conta", "NORMAL") != "TESTE":
        raise HTTPException(status_code=404, detail=MSG_404)
    return usuario
