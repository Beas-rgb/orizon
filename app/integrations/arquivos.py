"""Guarda o binário fora da resposta da API.

O caminho no disco não é URL pública. O download só acontece depois
da checagem de visibilidade no service.
"""

import hashlib
from pathlib import Path

from app.core.config import settings

RAIZ = Path("data/biblioteca")
LIMITE_BYTES = 10 * 1024 * 1024
MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "text/plain",
}


class ArquivoInvalido(Exception):
    pass


def _r2_pronto() -> bool:
    return bool(
        settings.r2_endpoint
        and settings.r2_bucket
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
    )


def _cliente_r2():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def _validar(conteudo: bytes, mime: str) -> str:
    if not conteudo:
        raise ArquivoInvalido("Arquivo vazio.")
    if len(conteudo) > LIMITE_BYTES:
        raise ArquivoInvalido("Arquivo maior que 10 MB.")
    if mime not in MIMES:
        raise ArquivoInvalido("Tipo de arquivo não permitido.")
    return hashlib.sha256(conteudo).hexdigest()


def guardar(documento_id: str, conteudo: bytes, mime: str) -> tuple[str, str]:
    resumo = _validar(conteudo, mime)
    if _r2_pronto():
        chave = f"biblioteca/{documento_id}"
        _cliente_r2().put_object(
            Bucket=settings.r2_bucket,
            Key=chave,
            Body=conteudo,
            ContentType=mime,
        )
        return f"r2:{chave}", resumo
    RAIZ.mkdir(parents=True, exist_ok=True)
    destino = RAIZ / documento_id
    destino.write_bytes(conteudo)
    return str(destino.as_posix()), resumo


def ler(key: str) -> bytes:
    if key.startswith("r2:"):
        objeto = _cliente_r2().get_object(
            Bucket=settings.r2_bucket,
            Key=key.removeprefix("r2:"),
        )
        return objeto["Body"].read()
    caminho = Path(key)
    if not caminho.is_file():
        raise FileNotFoundError(key)
    if "biblioteca" not in caminho.as_posix():
        raise FileNotFoundError(key)
    return caminho.read_bytes()
