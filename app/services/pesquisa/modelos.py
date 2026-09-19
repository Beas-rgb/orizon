"""Modelos (templates) de pesquisa."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.autorizacao import papel_no_projeto
from app.core.tokens import novo_id
from app.integrations.arquivos import ArquivoInvalido, copiar_midia
from app.models.base import agora
from app.models.pesquisa import (
    OpcaoResposta,
    Pergunta,
    Pesquisa,
    TemplateOpcao,
    TemplatePergunta,
    TemplatePesquisa,
)
from app.models.usuario import Usuario
from app.services.auditoria import registrar as _auditar
from app.services.identidade import ErroAuth
from app.services.pesquisa.comum import _pesquisa_viva


def salvar_modelo(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    nome: str,
) -> TemplatePesquisa:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    agora_ = agora()
    modelo = TemplatePesquisa(
        id=novo_id(),
        criado_por=consultor.id,
        nome=nome.strip(),
        descricao=pesquisa.descricao,
        tipo=pesquisa.tipo,
        categoria="generico",
        compartilhado=False,
        versao=1,
        ativo=True,
        organizacao_id=None,
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )
    db.add(modelo)
    db.flush()
    perguntas = db.scalars(
        select(Pergunta)
        .where(
            Pergunta.pesquisa_id == pesquisa.id,
            Pergunta.deleted_at.is_(None),
        )
        .order_by(Pergunta.ordem)
    ).all()
    for item in perguntas:
        midia_key = None
        midia_tipo = item.midia_tipo
        if item.midia_key:
            try:
                midia_key = copiar_midia(item.midia_key, novo_id())
            except (ArquivoInvalido, FileNotFoundError, OSError):
                midia_key = None
                midia_tipo = None
        copia = TemplatePergunta(
            id=novo_id(),
            template_id=modelo.id,
            texto=item.texto,
            tipo=item.tipo,
            obrigatoria=item.obrigatoria,
            ordem=item.ordem,
            midia_tipo=midia_tipo if midia_key else None,
            midia_key=midia_key,
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
        db.add(copia)
        db.flush()
        opcoes = db.scalars(
            select(OpcaoResposta)
            .where(OpcaoResposta.pergunta_id == item.id)
            .order_by(OpcaoResposta.ordem)
        ).all()
        for opcao in opcoes:
            db.add(
                TemplateOpcao(
                    id=novo_id(),
                    pergunta_template_id=copia.id,
                    texto=opcao.texto,
                    ordem=opcao.ordem,
                    criado_em=agora_,
                    atualizado_em=agora_,
                    deleted_at=None,
                )
            )
    _auditar(db, "MODELO_SALVO", consultor.id)
    db.commit()
    return modelo


def listar_modelos(db: Session, consultor: Usuario) -> list[TemplatePesquisa]:
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(404, "Modelo não encontrado.")
    return list(
        db.scalars(
            select(TemplatePesquisa)
            .where(
                TemplatePesquisa.deleted_at.is_(None),
                TemplatePesquisa.ativo.is_(True),
                TemplatePesquisa.criado_por == consultor.id,
            )
            .order_by(TemplatePesquisa.criado_em.desc())
        ).all()
    )


def criar_de_modelo(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    template_id: str,
    titulo: str | None,
) -> Pesquisa:
    if papel_no_projeto(db, consultor, projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    modelo = db.get(TemplatePesquisa, template_id)
    if (
        modelo is None
        or modelo.deleted_at is not None
        or not modelo.ativo
        or modelo.criado_por != consultor.id
    ):
        raise ErroAuth(404, "Modelo não encontrado.")
    agora_ = agora()
    pesquisa = Pesquisa(
        id=novo_id(),
        projeto_id=projeto_id,
        criado_por=consultor.id,
        titulo=(titulo or modelo.nome).strip(),
        descricao=modelo.descricao,
        tipo=modelo.tipo,
        status="RASCUNHO",
        bloqueada=False,
        criado_em=agora_,
        atualizado_em=agora_,
        template_origem_id=modelo.id,
    )
    db.add(pesquisa)
    db.flush()
    perguntas = db.scalars(
        select(TemplatePergunta)
        .where(
            TemplatePergunta.template_id == modelo.id,
            TemplatePergunta.deleted_at.is_(None),
        )
        .order_by(TemplatePergunta.ordem)
    ).all()
    for item in perguntas:
        midia_key = None
        midia_tipo = item.midia_tipo
        if item.midia_key:
            try:
                midia_key = copiar_midia(item.midia_key, novo_id())
            except (ArquivoInvalido, FileNotFoundError, OSError):
                midia_key = None
                midia_tipo = None
        pergunta = Pergunta(
            id=novo_id(),
            pesquisa_id=pesquisa.id,
            texto=item.texto,
            tipo=item.tipo,
            obrigatoria=item.obrigatoria,
            ordem=item.ordem,
            midia_tipo=midia_tipo if midia_key else None,
            midia_key=midia_key,
            criado_em=agora_,
            atualizado_em=agora_,
        )
        db.add(pergunta)
        db.flush()
        opcoes = db.scalars(
            select(TemplateOpcao)
            .where(
                TemplateOpcao.pergunta_template_id == item.id,
                TemplateOpcao.deleted_at.is_(None),
            )
            .order_by(TemplateOpcao.ordem)
        ).all()
        for opcao in opcoes:
            db.add(
                OpcaoResposta(
                    id=novo_id(),
                    pergunta_id=pergunta.id,
                    texto=opcao.texto,
                    ordem=opcao.ordem,
                    criado_em=agora_,
                )
            )
    _auditar(db, "PESQUISA_DE_MODELO", consultor.id)
    db.commit()
    return pesquisa
