"""Guarda o binário fora da resposta da API.

O caminho no disco não é URL pública. O download só acontece depois
da checagem de visibilidade no service.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import settings

RAIZ = Path("data/biblioteca")
RAIZ_MIDIA = Path("data/pesquisas")
LIMITE_BYTES = 10 * 1024 * 1024
LIMITE_IMAGEM = 5 * 1024 * 1024
LIMITE_VIDEO = 50 * 1024 * 1024
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIMES = {
    "application/pdf",
    DOCX,
    "image/png",
    "image/jpeg",
    "text/plain",
}
MIMES_IMAGEM = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MIMES_VIDEO = {"video/mp4", "video/webm"}


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
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(
            connect_timeout=10,
            read_timeout=30,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )


def detectar_mime(conteudo: bytes) -> str | None:
    """MIME real pelos bytes iniciais — não confia na extensão do cliente."""
    if len(conteudo) < 12:
        return None
    if conteudo[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if conteudo[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if conteudo[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    if conteudo[4:8] == b"ftyp":
        return "video/mp4"
    if conteudo[:4] == b"\x1a\x45\xdf\xa3":
        return "video/webm"
    return None


def _assinatura_documento(conteudo: bytes) -> str | None:
    """MIME real de documento. None quando não há assinatura conhecida."""
    if conteudo[:5] == b"%PDF-":
        return "application/pdf"
    if conteudo[:4] == b"PK\x03\x04":
        return DOCX
    return detectar_mime(conteudo)


def _parece_texto(conteudo: bytes) -> bool:
    """Texto puro de verdade: UTF-8, sem byte nulo e sem cara de HTML."""
    if b"\x00" in conteudo:
        return False
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return not texto.lstrip().startswith("<")


def _validar(conteudo: bytes, mime: str) -> str:
    if not conteudo:
        raise ArquivoInvalido("Arquivo vazio.")
    if len(conteudo) > LIMITE_BYTES:
        raise ArquivoInvalido("Arquivo maior que 10 MB.")
    if mime not in MIMES:
        raise ArquivoInvalido("Tipo de arquivo não permitido.")
    # O navegador declara o Content-Type; quem manda são os bytes. Sem isto,
    # um HTML com script entraria na biblioteca rotulado como PDF.
    real = _assinatura_documento(conteudo)
    if real is None:
        if mime != "text/plain" or not _parece_texto(conteudo):
            raise ArquivoInvalido("O conteúdo não corresponde ao tipo enviado.")
    elif real != mime:
        raise ArquivoInvalido("O conteúdo não corresponde ao tipo enviado.")
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


def guardar_midia(objeto_id: str, conteudo: bytes) -> tuple[str, str, str]:
    """Salva mídia de pergunta. Devolve (key, midia_tipo, mime)."""
    if not conteudo:
        raise ArquivoInvalido("Arquivo vazio.")
    mime = detectar_mime(conteudo)
    if mime is None:
        raise ArquivoInvalido("Tipo de mídia não permitido.")
    if mime in MIMES_IMAGEM:
        if len(conteudo) > LIMITE_IMAGEM:
            raise ArquivoInvalido("Imagem maior que 5 MB.")
        midia_tipo = "IMAGEM"
    elif mime in MIMES_VIDEO:
        if len(conteudo) > LIMITE_VIDEO:
            raise ArquivoInvalido("Vídeo maior que 50 MB.")
        midia_tipo = "VIDEO"
    else:
        raise ArquivoInvalido("Tipo de mídia não permitido.")
    if _r2_pronto():
        chave = f"pesquisas/{objeto_id}"
        _cliente_r2().put_object(
            Bucket=settings.r2_bucket,
            Key=chave,
            Body=conteudo,
            ContentType=mime,
        )
        return f"r2:{chave}", midia_tipo, mime
    RAIZ_MIDIA.mkdir(parents=True, exist_ok=True)
    destino = RAIZ_MIDIA / objeto_id
    destino.write_bytes(conteudo)
    return str(destino.as_posix()), midia_tipo, mime


def copiar_midia(chave_origem: str, novo_id: str) -> str:
    """Copia bytes para nova chave interna (modelo ↔ pesquisa)."""
    conteudo = ler_midia(chave_origem)
    chave, _tipo, _mime = guardar_midia(novo_id, conteudo)
    return chave


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


def ler_midia(key: str) -> bytes:
    if key.startswith("r2:"):
        objeto = _cliente_r2().get_object(
            Bucket=settings.r2_bucket,
            Key=key.removeprefix("r2:"),
        )
        return objeto["Body"].read()
    caminho = Path(key)
    if not caminho.is_file():
        raise FileNotFoundError(key)
    posix = caminho.as_posix()
    if "pesquisas" not in posix and "biblioteca" not in posix:
        raise FileNotFoundError(key)
    return caminho.read_bytes()
