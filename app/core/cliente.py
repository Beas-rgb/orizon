"""IP do cliente. Com hops 0, o cabeçalho enviado pelo navegador é ignorado."""

import ipaddress

from fastapi import Request

from app.core.config import settings


def ip_do_cliente(request: Request) -> str | None:
    host = request.client.host if request.client else None
    saltos = settings.trusted_proxy_hops
    if saltos <= 0:
        return host
    bruto = request.headers.get("x-forwarded-for", "")
    partes = [item.strip() for item in bruto.split(",") if item.strip()]
    if len(partes) < saltos:
        return host
    candidato = partes[-saltos]
    try:
        ipaddress.ip_address(candidato)
    except ValueError:
        return host
    return candidato
