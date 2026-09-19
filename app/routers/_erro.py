"""Helper de rota: ErroAuth do service → HTTPException."""

from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException

from app.services.identidade import ErroAuth

T = TypeVar("T")


def chamar(acao: Callable[[], T]) -> T:
    try:
        return acao()
    except ErroAuth as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalhe) from None
