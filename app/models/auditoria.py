from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LogAuditoria(Base):
    """Ação relevante. Sem senha, token ou hash."""

    __tablename__ = "logs_auditoria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    acao: Mapped[str] = mapped_column(String(64))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
