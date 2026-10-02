"""Helper de rota: ErroAuth do service → HTTPException."""

from collections.abc import Callable

from fastapi import HTTPException

from app.services.identidade import ErroAuth


def chamar[T](acao: Callable[[], T]) -> T:
    try:
        return acao()
    except ErroAuth as exc:
        headers = None
        if exc.retry_after is not None:
            headers = {"Retry-After": str(exc.retry_after)}
        raise HTTPException(
            status_code=exc.status,
            detail=exc.detalhe,
            headers=headers,
        ) from None
