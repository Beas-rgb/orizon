"""Upload e download de mídia das perguntas."""

from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.integrations.arquivos import ArquivoInvalido, guardar_midia, ler_midia
from app.models.base import agora
from app.models.pesquisa import Pergunta
from app.models.usuario import Usuario
from app.services.auditoria import registrar as _auditar
from app.services.identidade import ErroAuth

from app.services.pesquisa.crud import _exigir_rascunho_consultor


def anexar_midia_pergunta(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
    conteudo: bytes,
) -> Pergunta:
    """Upload de foto/vídeo. Só em RASCUNHO. Chave interna, nunca o nome do arquivo."""
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
    ):
        raise ErroAuth(404, "Pergunta não encontrada.")
    objeto_id = novo_id()
    try:
        chave, midia_tipo, _mime = guardar_midia(objeto_id, conteudo)
    except ArquivoInvalido as exc:
        raise ErroAuth(422, str(exc)) from None
    pergunta.midia_key = chave
    pergunta.midia_tipo = midia_tipo
    pergunta.atualizado_em = agora()
    pesquisa.atualizado_em = pergunta.atualizado_em
    _auditar(db, "PERGUNTA_MIDIA", consultor.id)
    db.commit()
    return pergunta


def remover_midia_pergunta(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
) -> Pergunta:
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
    ):
        raise ErroAuth(404, "Pergunta não encontrada.")
    pergunta.midia_key = None
    pergunta.midia_tipo = None
    pergunta.atualizado_em = agora()
    pesquisa.atualizado_em = pergunta.atualizado_em
    _auditar(db, "PERGUNTA_MIDIA_REMOVIDA", consultor.id)
    db.commit()
    return pergunta


def baixar_midia_pergunta(
    db: Session,
    usuario: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
) -> tuple[bytes, str]:
    """Consultora (qualquer status). Órgão/funcionário só PUBLICADA/ENCERRADA."""
    from app.core.autorizacao import exigir_midia_pesquisa, exigir_pesquisa_viva

    pesquisa = exigir_pesquisa_viva(db, pesquisa_id)
    exigir_midia_pesquisa(db, usuario, pesquisa)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
        or not pergunta.midia_key
    ):
        raise ErroAuth(404, "Mídia não encontrada.")
    try:
        conteudo = ler_midia(pergunta.midia_key)
    except FileNotFoundError:
        raise ErroAuth(404, "Mídia não encontrada.") from None
    mime = "application/octet-stream"
    if pergunta.midia_tipo == "IMAGEM":
        mime = "image/jpeg"
    elif pergunta.midia_tipo == "VIDEO":
        mime = "video/mp4"
    from app.integrations.arquivos import detectar_mime

    detectado = detectar_mime(conteudo)
    if detectado:
        mime = detectado
    return conteudo, mime


def baixar_midia_pelo_token(
    db: Session,
    token: str,
    pergunta_id: str,
    usuario: Usuario,
) -> tuple[bytes, str]:
    """Mesma autorização do formulário de resposta."""
    from app.services.pesquisa.resposta import _token_convite

    linha = _token_convite(db, token)
    return baixar_midia_da_pesquisa(db, linha.pesquisa_id, pergunta_id, usuario)


def baixar_midia_da_pesquisa(
    db: Session,
    pesquisa_id: str,
    pergunta_id: str,
    usuario: Usuario,
) -> tuple[bytes, str]:
    from app.services.pesquisa.resposta import (
        _exigir_pesquisa_aberta,
        _participante_da_pesquisa,
    )

    pesquisa = _exigir_pesquisa_aberta(db, pesquisa_id)
    _participante_da_pesquisa(db, usuario, pesquisa, para_envio=False)
    db.commit()
    return baixar_midia_pergunta(db, usuario, pesquisa.id, pergunta_id)
