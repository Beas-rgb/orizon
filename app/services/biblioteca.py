"""Quem pode ver o arquivo. A tela não escolhe isso sozinha.

Se a consultora só envia, sem dizer a audiência, o arquivo nasce PRIVADO
e só ela baixa. Conhecer o ID não libera o arquivo de outro cliente.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.integrations.arquivos import ArquivoInvalido, guardar, ler
from app.models.auditoria import LogAuditoria
from app.models.base import agora
from app.models.documento import Documento
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth

VISIBILIDADES_INTERNA = {"PRIVADO", "ORGAO", "FUNCIONARIOS", "PUBLICO_PROJETO"}


def _auditar(db: Session, acao: str, usuario_id: str) -> None:
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=usuario_id,
            acao=acao,
            criado_em=agora(),
        )
    )


def _papel_no_projeto(db: Session, usuario: Usuario, projeto_id: str) -> str | None:
    projeto = db.get(Projeto, projeto_id)
    if projeto is None or projeto.deleted_at is not None:
        return None
    if usuario.id == projeto.consultor_id:
        return "CONSULTOR"
    vinculo = db.scalar(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    if vinculo is None:
        return None
    return vinculo.papel


def pode_ver(db: Session, usuario: Usuario, doc: Documento) -> bool:
    if usuario.papel == "TI" or doc.deleted_at is not None:
        return False
    if doc.consultor_id == usuario.id:
        return True
    if doc.camada in {"PRINCIPAL", "EXTERNA"} or doc.visibilidade == "PRIVADO":
        return False
    if doc.projeto_id is None:
        return False
    papel = _papel_no_projeto(db, usuario, doc.projeto_id)
    if papel is None or papel == "CONSULTOR":
        return False
    if doc.camada != "INTERNA":
        return False
    if doc.visibilidade == "ORGAO":
        return papel == "ORGAO"
    if doc.visibilidade == "FUNCIONARIOS":
        return papel == "FUNCIONARIO"
    if doc.visibilidade == "PUBLICO_PROJETO":
        return papel in {"ORGAO", "FUNCIONARIO"}
    return False


def _resolver_camada(
    projeto_id: str | None,
    camada: str | None,
    visibilidade: str | None,
) -> tuple[str, str]:
    """Sem escolha explícita, fica privado só para a consultora."""
    if projeto_id is None:
        return "PRINCIPAL", "PRIVADO"
    if camada is None or camada == "EXTERNA":
        return "EXTERNA", "PRIVADO"
    if camada != "INTERNA":
        raise ErroAuth(422, "Camada inválida.")
    escolhida = visibilidade or "PRIVADO"
    if escolhida not in VISIBILIDADES_INTERNA:
        raise ErroAuth(422, "Visibilidade inválida.")
    return "INTERNA", escolhida


def enviar(
    db: Session,
    consultor: Usuario,
    nome: str,
    mime: str,
    conteudo: bytes,
    projeto_id: str | None,
    camada: str | None,
    visibilidade: str | None,
) -> Documento:
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(403, "Só a consultora envia arquivo.")
    dona = _papel_no_projeto(db, consultor, projeto_id) if projeto_id else None
    if projeto_id is not None and dona != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    camada_final, visivel = _resolver_camada(projeto_id, camada, visibilidade)
    doc_id = novo_id()
    try:
        key, resumo = guardar(doc_id, conteudo, mime)
    except ArquivoInvalido as exc:
        raise ErroAuth(422, str(exc)) from None
    doc = Documento(
        id=doc_id,
        consultor_id=consultor.id,
        projeto_id=projeto_id,
        camada=camada_final,
        visibilidade=visivel,
        nome=nome.strip()[:200],
        mime=mime,
        tamanho=len(conteudo),
        sha256=resumo,
        armazenamento_key=key,
    )
    db.add(doc)
    _auditar(db, "DOCUMENTO_CRIADO", consultor.id)
    db.commit()
    return doc


def listar(
    db: Session,
    usuario: Usuario,
    projeto_id: str | None,
) -> list[Documento]:
    if usuario.papel == "TI":
        raise ErroAuth(403, "Sem acesso à biblioteca.")
    consulta = select(Documento).where(Documento.deleted_at.is_(None))
    if projeto_id is not None:
        if _papel_no_projeto(db, usuario, projeto_id) is None:
            raise ErroAuth(404, "Projeto não encontrado.")
        consulta = consulta.where(Documento.projeto_id == projeto_id)
    else:
        proprios = Documento.consultor_id == usuario.id
        if usuario.papel == "CONSULTOR":
            consulta = consulta.where(
                or_(proprios, Documento.camada == "INTERNA")
            )
        else:
            consulta = consulta.where(Documento.camada == "INTERNA")
    docs = list(db.scalars(consulta).all())
    return [doc for doc in docs if pode_ver(db, usuario, doc)]


def obter(db: Session, usuario: Usuario, documento_id: str) -> Documento:
    doc = db.get(Documento, documento_id)
    if doc is None or not pode_ver(db, usuario, doc):
        raise ErroAuth(404, "Arquivo não encontrado.")
    return doc


def baixar(db: Session, usuario: Usuario, documento_id: str) -> tuple[Documento, bytes]:
    doc = obter(db, usuario, documento_id)
    try:
        conteudo = ler(doc.armazenamento_key)
    except FileNotFoundError:
        raise ErroAuth(404, "Arquivo não encontrado.") from None
    _auditar(db, "DOCUMENTO_BAIXADO", usuario.id)
    db.commit()
    return doc, conteudo


def definir_visibilidade(
    db: Session,
    consultor: Usuario,
    documento_id: str,
    visibilidade: str,
) -> Documento:
    """Só a dona muda quem vê. Biblioteca externa e principal continuam privadas."""
    doc = db.get(Documento, documento_id)
    if (
        doc is None
        or doc.deleted_at is not None
        or doc.consultor_id != consultor.id
    ):
        raise ErroAuth(404, "Arquivo não encontrado.")
    if doc.camada != "INTERNA":
        raise ErroAuth(422, "Fora da biblioteca interna o arquivo fica só com você.")
    if visibilidade not in VISIBILIDADES_INTERNA:
        raise ErroAuth(422, "Visibilidade inválida.")
    doc.visibilidade = visibilidade
    doc.atualizado_em = agora()
    _auditar(db, "DOCUMENTO_VISIBILIDADE", consultor.id)
    db.commit()
    return doc


def enviar_para_projeto(
    db: Session,
    consultor: Usuario,
    documento_id: str,
    projeto_id: str,
) -> Documento:
    """Copia o vínculo da principal para o projeto, ainda privado."""
    origem = obter(db, consultor, documento_id)
    if origem.camada != "PRINCIPAL":
        raise ErroAuth(422, "Só a biblioteca principal envia para um projeto.")
    if _papel_no_projeto(db, consultor, projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    try:
        conteudo = ler(origem.armazenamento_key)
    except FileNotFoundError:
        raise ErroAuth(404, "Arquivo não encontrado.") from None
    return enviar(
        db,
        consultor,
        origem.nome,
        origem.mime,
        conteudo,
        projeto_id,
        "EXTERNA",
        None,
    )
