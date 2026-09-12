"""Consulta pública de CNPJ. O nome do órgão não é digitado à mão.

A fonte padrão é a BrasilAPI. Testes trocam `buscar` para não depender
da rede. CNPJ inválido ou inexistente não cria projeto.
"""

import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BRASIL_API = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


class CnpjInvalido(Exception):
    pass


class CnpjNaoEncontrado(Exception):
    pass


class CnpjIndisponivel(Exception):
    pass


@dataclass
class DadosCnpj:
    cnpj: str
    razao_social: str
    nome_fantasia: str | None
    municipio: str | None
    uf: str | None


def normalizar_cnpj(valor: str) -> str:
    """Aceita CNPJ numérico clássico e o novo alfanumérico (14 caracteres)."""
    bruto = re.sub(r"[^0-9A-Za-z]", "", (valor or "").upper())
    if len(bruto) != 14:
        raise CnpjInvalido("CNPJ deve ter 14 caracteres (numérico ou alfanumérico).")
    if not re.fullmatch(r"[0-9A-Z]{14}", bruto):
        raise CnpjInvalido("CNPJ inválido.")
    return bruto


def buscar(cnpj: str) -> DadosCnpj:
    numero = normalizar_cnpj(cnpj)
    pedido = Request(
        BRASIL_API.format(cnpj=numero),
        headers={"Accept": "application/json", "User-Agent": "horizon"},
    )
    try:
        with urlopen(pedido, timeout=10) as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise CnpjNaoEncontrado("CNPJ não encontrado.") from None
        raise CnpjIndisponivel("Consulta de CNPJ indisponível.") from None
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise CnpjIndisponivel("Consulta de CNPJ indisponível.") from exc

    razao = (corpo.get("razao_social") or "").strip()
    if not razao:
        raise CnpjNaoEncontrado("CNPJ sem razão social.")
    fantasia = (corpo.get("nome_fantasia") or "").strip() or None
    return DadosCnpj(
        cnpj=numero,
        razao_social=razao[:200],
        nome_fantasia=fantasia[:200] if fantasia else None,
        municipio=(corpo.get("municipio") or None),
        uf=(corpo.get("uf") or None),
    )
