"""Ciclo de avaliação de desempenho e relações avaliador-avaliado."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo


class CicloAvaliacao(IdTempo, Base):
    """Um ciclo de desempenho. Preserva configuração, perguntas e resultados."""

    __tablename__ = "ciclos_avaliacao"

    projeto_id: Mapped[str] = mapped_column(ForeignKey("projetos.id"), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    inicio_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    fim_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Escopo: ORGANIZACAO, SETOR, CARGO, MANUAL.
    escopo: Mapped[str] = mapped_column(String(32), default="ORGANIZACAO")
    # JSON: perspectivas, pesos, ordem, regras. Nunca código do usuário.
    configuracao: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="RASCUNHO")
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AvaliacaoRelacionamento(Base):
    """Quem avalia quem. O único lugar que liga avaliador a avaliado."""

    __tablename__ = "avaliacao_relacionamentos"
    __table_args__ = (
        UniqueConstraint(
            "ciclo_id",
            "avaliador_id",
            "avaliado_id",
            "tipo_relacao",
            name="uq_avaliacao_relacionamento",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ciclo_id: Mapped[str] = mapped_column(
        ForeignKey("ciclos_avaliacao.id"),
        index=True,
    )
    avaliador_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    avaliado_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    # AUTO, SUPERIOR, SUBORDINADO.
    tipo_relacao: Mapped[str] = mapped_column(String(32))
    perspectiva_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    peso: Mapped[float] = mapped_column(default=1.0)
    status: Mapped[str] = mapped_column(String(32), default="PENDENTE")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AvaliacaoResposta(Base):
    """Nota de uma pergunta dentro de uma relação. Não usa token de pesquisa."""

    __tablename__ = "avaliacao_respostas"
    __table_args__ = (
        UniqueConstraint(
            "relacionamento_id",
            "pergunta_id",
            name="uq_avaliacao_resposta_relacao_pergunta",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    relacionamento_id: Mapped[str] = mapped_column(
        ForeignKey("avaliacao_relacionamentos.id"),
        index=True,
    )
    pergunta_id: Mapped[str] = mapped_column(ForeignKey("perguntas.id"), index=True)
    valor_numerico: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    valor_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    opcao_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    respondido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
