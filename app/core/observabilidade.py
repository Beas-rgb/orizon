"""Log de acesso. Método, caminho e status. Sem corpo, token ou senha."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("horizon.acesso")


def caminho_seguro(path: str) -> str:
    if path.startswith("/responder/"):
        return "/responder/[token]"
    return path


class LogAcesso(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        inicio = time.perf_counter()
        resposta = await call_next(request)
        ms = int((time.perf_counter() - inicio) * 1000)
        logger.info(
            "%s %s %s %sms",
            request.method,
            caminho_seguro(request.url.path),
            resposta.status_code,
            ms,
        )
        return resposta
