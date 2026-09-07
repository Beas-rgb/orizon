from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo


class Setor(IdTempo, Base):
    """Área do órgão dentro do projeto. Sem isso a pesquisa não sabe de onde veio."""

    __tablename__ = "setores"

    projeto_id: Mapped[str] = mapped_column(ForeignKey("projetos.id"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
