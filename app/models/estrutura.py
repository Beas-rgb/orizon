"""Cargo e hierarquia do funcionário dentro do projeto."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo


class Cargo(IdTempo, Base):
    """Função dentro do projeto. Não é a mesma coisa que setor."""

    __tablename__ = "cargos"
    __table_args__ = (
        UniqueConstraint("projeto_id", "nome", name="uq_cargo_projeto_nome"),
    )

    projeto_id: Mapped[str] = mapped_column(ForeignKey("projetos.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class PerfilFuncionario(IdTempo, Base):
    """Vínculo organizacional do funcionário no projeto.

    setor_id segmenta; superior_id define a hierarquia. A árvore vem do
    superior, não do setor.
    """

    __tablename__ = "perfis_funcionario"
    __table_args__ = (
        UniqueConstraint(
            "projeto_id",
            "usuario_id",
            name="uq_perfil_funcionario_projeto_usuario",
        ),
    )

    projeto_id: Mapped[str] = mapped_column(ForeignKey("projetos.id"), index=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    setor_id: Mapped[str | None] = mapped_column(
        ForeignKey("setores.id"),
        nullable=True,
    )
    cargo_id: Mapped[str | None] = mapped_column(
        ForeignKey("cargos.id"),
        nullable=True,
    )
    superior_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
