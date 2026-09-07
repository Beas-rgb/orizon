from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notificacao(Base):
    """Aviso interno. Só o dono lê. Sem token e sem senha no texto."""

    __tablename__ = "notificacoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    projeto_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tipo: Mapped[str] = mapped_column(String(32))
    titulo: Mapped[str] = mapped_column(String(160))
    mensagem: Mapped[str] = mapped_column(Text)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    lida_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    prioridade: Mapped[str] = mapped_column(String(16), default="normal")


class EntregaMensagem(Base):
    """Evento de entrega. O corpo com token não entra aqui.

    canal=EMAIL sai agora. TELEFONE fica gravado como NAO_HABILITADO
    até existir provedor de SMS.
    """

    __tablename__ = "entregas_mensagem"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canal: Mapped[str] = mapped_column(String(16))
    destino: Mapped[str] = mapped_column(String(255))
    assunto: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32))
    referencia: Mapped[str] = mapped_column(String(40))
    projeto_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    usuario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    erro: Mapped[str | None] = mapped_column(String(160), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    enviado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
