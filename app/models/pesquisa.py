from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Pesquisa(Base):
    """Pesquisa do projeto. Clima não revela quem respondeu."""

    __tablename__ = "pesquisas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    projeto_id: Mapped[str] = mapped_column(String(36), index=True)
    criado_por: Mapped[str] = mapped_column(String(36))
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(32), default="RASCUNHO")
    bloqueada: Mapped[bool] = mapped_column(Boolean, default=False)
    publicada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    encerrada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    disponivel_de: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    disponivel_ate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    template_origem_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Pergunta(Base):
    __tablename__ = "perguntas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pesquisa_id: Mapped[str] = mapped_column(ForeignKey("pesquisas.id"), index=True)
    texto: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(40))
    obrigatoria: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(SmallInteger, default=1)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class OpcaoResposta(Base):
    __tablename__ = "opcoes_resposta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pergunta_id: Mapped[str] = mapped_column(ForeignKey("perguntas.id"), index=True)
    texto: Mapped[str] = mapped_column(String(200))
    ordem: Mapped[int] = mapped_column(SmallInteger, default=1)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TokenResposta(Base):
    """Link de resposta. Não guarda o nome de quem vai responder."""

    __tablename__ = "tokens_resposta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pesquisa_id: Mapped[str] = mapped_column(ForeignKey("pesquisas.id"), index=True)
    setor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    token: Mapped[str] = mapped_column(String(36), unique=True)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    usado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expira_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TemplatePesquisa(Base):
    """Modelo reutilizável. Só a consultora dona vê o que não é compartilhado."""

    __tablename__ = "templates_pesquisa"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    criado_por: Mapped[str] = mapped_column(String(36))
    nome: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str] = mapped_column(String(40))
    categoria: Mapped[str] = mapped_column(String(32), default="generico")
    compartilhado: Mapped[bool] = mapped_column(Boolean, default=False)
    versao: Mapped[int] = mapped_column(SmallInteger, default=1)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    organizacao_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class TemplatePergunta(Base):
    __tablename__ = "template_perguntas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(36), index=True)
    texto: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(40))
    obrigatoria: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(SmallInteger, default=1)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class TemplateOpcao(Base):
    __tablename__ = "template_opcoes_resposta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pergunta_template_id: Mapped[str] = mapped_column(String(36), index=True)
    texto: Mapped[str] = mapped_column(String(200))
    ordem: Mapped[int] = mapped_column(SmallInteger, default=1)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Resposta(Base):
    __tablename__ = "respostas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_id: Mapped[str] = mapped_column(ForeignKey("tokens_resposta.id"), index=True)
    pergunta_id: Mapped[str] = mapped_column(ForeignKey("perguntas.id"))
    valor_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_numerico: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    opcao_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    respondido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
