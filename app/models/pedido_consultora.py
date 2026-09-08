from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PedidoConsultora(Base):
    """Pedido de conta da consultora. Não é login. Expira em 5 dias."""

    __tablename__ = "pedidos_consultora"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDENTE")
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    autorizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    autorizado_por_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
