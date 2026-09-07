import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def agora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class IdTempo:
    """Colunas comuns. Soft delete e atualizado_em entram nas mutations."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=agora,
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=agora,
        onupdate=agora,
    )
