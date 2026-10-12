"""Tarefa longa com job_id: importação, convites, exportação."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

STATUS_TAREFA = ("PENDENTE", "EXECUTANDO", "CONCLUIDA", "FALHOU")


class Tarefa(Base):
    """Estado e progresso. O resultado detalhado fica na tabela de destino."""

    __tablename__ = "tarefas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dono_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    projeto_id: Mapped[str | None] = mapped_column(
        ForeignKey("projetos.id"),
        nullable=True,
    )
    tipo: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(16), default="PENDENTE", server_default="PENDENTE"
    )
    feito: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    falhas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    erro: Mapped[str | None] = mapped_column(String(160), nullable=True)
    resumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    concluido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
