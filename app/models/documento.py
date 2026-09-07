from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo


class Documento(IdTempo, Base):
    """Arquivo da biblioteca. Quem vê é decidido aqui, não na tela.

    Padrão: PRIVADO, só a consultora dona. PRINCIPAL e EXTERNA não abrem
    para órgão nem funcionário. INTERNA só muda se ela escolher explicitamente.
    """

    __tablename__ = "documentos"

    consultor_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"), index=True)
    projeto_id: Mapped[str | None] = mapped_column(
        ForeignKey("projetos.id"),
        nullable=True,
        index=True,
    )
    camada: Mapped[str] = mapped_column(String(32))
    visibilidade: Mapped[str] = mapped_column(String(32), default="PRIVADO")
    nome: Mapped[str] = mapped_column(String(200))
    mime: Mapped[str] = mapped_column(String(120))
    tamanho: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    armazenamento_key: Mapped[str] = mapped_column(String(255))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
