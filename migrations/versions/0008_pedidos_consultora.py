"""Pedidos de conta da consultora. Não apaga dado."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0008_pedidos_consultora"
down_revision: str | None = "0007_usuario_telefone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _existe("pedidos_consultora"):
        return
    op.create_table(
        "pedidos_consultora",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("autorizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("autorizado_por_id", sa.String(36), nullable=True),
    )


def downgrade() -> None:
    if _existe("pedidos_consultora"):
        op.drop_table("pedidos_consultora")
