"""Biblioteca. A visibilidade é decidida neste backend, não no cliente.

Quem só envia o arquivo, sem audiência, recebe PRIVADO. Download e lista
escondem o que a pessoa não pode ver — o ID sozinho não abre o arquivo.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.services.biblioteca import (
    baixar,
    definir_visibilidade,
    enviar,
    enviar_para_projeto,
    listar,
    obter,
)
from app.services.identidade import ErroAuth

router = APIRouter(prefix="/biblioteca", tags=["biblioteca"])


class DocumentoSaida(BaseModel):
    id: str
    nome: str
    camada: str
    visibilidade: str
    projeto_id: str | None
    mime: str
    tamanho: int


class VisibilidadeEntrada(BaseModel):
    visibilidade: str = Field(min_length=3, max_length=32)


class EnviarProjetoEntrada(BaseModel):
    projeto_id: str = Field(min_length=1, max_length=36)


def _chamar(acao):
    try:
        return acao()
    except ErroAuth as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalhe) from None


def _saida(doc) -> DocumentoSaida:
    return DocumentoSaida(
        id=doc.id,
        nome=doc.nome,
        camada=doc.camada,
        visibilidade=doc.visibilidade,
        projeto_id=doc.projeto_id,
        mime=doc.mime,
        tamanho=doc.tamanho,
    )


@router.post("", response_model=DocumentoSaida)
async def criar(
    arquivo: UploadFile = File(...),
    projeto_id: str | None = Form(default=None),
    camada: str | None = Form(default=None),
    visibilidade: str | None = Form(default=None),
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> DocumentoSaida:
    """Upload. Sem camada e sem visibilidade, o arquivo fica só com a consultora."""
    conteudo = await arquivo.read()
    mime = arquivo.content_type or "application/octet-stream"
    nome = arquivo.filename or "arquivo"
    doc = _chamar(
        lambda: enviar(
            db,
            consultor,
            nome,
            mime,
            conteudo,
            projeto_id or None,
            camada,
            visibilidade,
        )
    )
    return _saida(doc)


@router.get("", response_model=list[DocumentoSaida])
def lista(
    projeto_id: str | None = None,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[DocumentoSaida]:
    docs = _chamar(lambda: listar(db, usuario, projeto_id))
    return [_saida(doc) for doc in docs]


@router.get("/{documento_id}", response_model=DocumentoSaida)
def detalhe(
    documento_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> DocumentoSaida:
    return _saida(_chamar(lambda: obter(db, usuario, documento_id)))


@router.get("/{documento_id}/arquivo")
def arquivo(
    documento_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    doc, conteudo = _chamar(lambda: baixar(db, usuario, documento_id))
    return Response(
        content=conteudo,
        media_type=doc.mime,
        headers={"Content-Disposition": f'attachment; filename="{doc.nome}"'},
    )


@router.patch("/{documento_id}", response_model=DocumentoSaida)
def visibilidade(
    documento_id: str,
    corpo: VisibilidadeEntrada,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> DocumentoSaida:
    doc = _chamar(
        lambda: definir_visibilidade(
            db, consultor, documento_id, corpo.visibilidade
        )
    )
    return _saida(doc)


@router.post("/{documento_id}/enviar", response_model=DocumentoSaida)
def para_projeto(
    documento_id: str,
    corpo: EnviarProjetoEntrada,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> DocumentoSaida:
    """Copia da principal para o projeto. Continua privado."""
    doc = _chamar(
        lambda: enviar_para_projeto(db, consultor, documento_id, corpo.projeto_id)
    )
    return _saida(doc)
