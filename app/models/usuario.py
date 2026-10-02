from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo

TIPOS_CONTA = ("NORMAL", "TESTE", "SINTETICO")


class Usuario(IdTempo, Base):
    """Conta de acesso. A senha fica só como hash. Sem organizacao_id: o
    vínculo com o cliente entra na Fase 2, via projeto."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "tipo_conta IN ('NORMAL', 'TESTE', 'SINTETICO')",
            name="ck_usuarios_tipo_conta",
        ),
    )

    nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    senha_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    papel: Mapped[str] = mapped_column(String(32))
    tipo_conta: Mapped[str] = mapped_column(
        String(16),
        default="NORMAL",
        server_default="NORMAL",
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    tentativas_falhas: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
