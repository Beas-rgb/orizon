"""Log de acesso. Método, caminho, status e request_id. Sem corpo/token/senha."""

from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("horizon.acesso")


def caminho_seguro(path: str) -> str:
    if path.startswith("/responder/") and not path.startswith(
        "/responder/pesquisa/"
    ):
        return "/responder/[token]"
    return path


class LogAcesso(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        inicio = time.perf_counter()
        resposta = await call_next(request)
        ms = int((time.perf_counter() - inicio) * 1000)
        resposta.headers["X-Request-Id"] = request_id
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": caminho_seguro(request.url.path),
                    "status": resposta.status_code,
                    "ms": ms,
                },
                ensure_ascii=False,
            )
        )
        return resposta
