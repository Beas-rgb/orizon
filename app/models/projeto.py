from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo


class RotuloProjeto(Base):
    """Rótulo da lista de projetos. A tela só exibe o que está aqui."""

    __tablename__ = "rotulos_projeto"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    nome: Mapped[str] = mapped_column(String(80))
    ordem: Mapped[int] = mapped_column(Integer)


class Projeto(IdTempo, Base):
    """Um trabalho da consultora para um órgão. O edital/documento é o
    vínculo de criação; o arquivo no R2 entra na biblioteca."""

    __tablename__ = "projetos"

    organizacao_id: Mapped[str] = mapped_column(ForeignKey("organizacoes.id"))
    consultor_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    rotulo_id: Mapped[str] = mapped_column(ForeignKey("rotulos_projeto.id"))
    estado: Mapped[str] = mapped_column(String(32), default="ABERTO")
    vinculo_tipo: Mapped[str] = mapped_column(String(32))
    vinculo_titulo: Mapped[str] = mapped_column(String(200))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ProjetoUsuario(Base):
    """Quem pode ver o projeto. Sem esta linha, conhecer o ID não libera."""

    __tablename__ = "projeto_usuarios"
    __table_args__ = (
        UniqueConstraint("projeto_id", "usuario_id", name="uq_projeto_usuario"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    projeto_id: Mapped[str] = mapped_column(ForeignKey("projetos.id"), index=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    papel: Mapped[str] = mapped_column(String(32))
