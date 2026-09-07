from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ControleAcesso(Base):
    """Contagem de tentativas no banco, por e-mail e tipo de ação.

    3 falhas bloqueiam a chave por 5 minutos. Vale para login e para
    pedido de recuperação. Fica no Postgres para sobreviver a reinício
    e a mais de um processo da API — um contador só na memória não basta.
    """

    __tablename__ = "controle_acesso"

    chave: Mapped[str] = mapped_column(String(280), primary_key=True)
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_ate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
