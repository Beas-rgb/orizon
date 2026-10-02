"""Laboratório: cenários sintéticos. Só contas TESTE com ENABLE_LAB."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CenarioLab(Base):
    """Um cenário = uma organização e um projeto próprios, todos sintéticos."""

    __tablename__ = "cenarios_lab"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dono_id: Mapped[str] = mapped_column(
        ForeignKey("usuarios.id"),
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(160))
    tipo: Mapped[str] = mapped_column(String(32))
    tamanho: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)
    perfil: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    projeto_id: Mapped[str | None] = mapped_column(
        ForeignKey("projetos.id"),
        nullable=True,
    )
    progresso: Mapped[int] = mapped_column(Integer, default=0)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
