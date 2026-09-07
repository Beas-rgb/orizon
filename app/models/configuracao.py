from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTempo


class ConfiguracaoProjeto(IdTempo, Base):
    """Regras do projeto. A IA nasce e permanece DESATIVADA até o Horizon
    estar em uso. Não há endpoint que ligue a IA nesta etapa."""

    __tablename__ = "configuracoes_projeto"

    projeto_id: Mapped[str] = mapped_column(
        ForeignKey("projetos.id"),
        unique=True,
    )
    pesquisas_habilitadas: Mapped[bool] = mapped_column(Boolean, default=False)
    ia_modo: Mapped[str] = mapped_column(String(32), default="DESATIVADA")
