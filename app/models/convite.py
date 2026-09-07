from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo


class Convite(IdTempo, Base):
    """Convite de primeiro acesso. O e-mail leva o token, nunca a senha."""

    __tablename__ = "convites"

    email: Mapped[str] = mapped_column(String(255), index=True)
    nome: Mapped[str] = mapped_column(String(160))
    papel: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDENTE")
    entrega: Mapped[str] = mapped_column(String(32), default="NAO_ENVIADO")
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    aceito_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    convidado_por_id: Mapped[str | None] = mapped_column(
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    projeto_id: Mapped[str | None] = mapped_column(
        ForeignKey("projetos.id"),
        nullable=True,
    )
