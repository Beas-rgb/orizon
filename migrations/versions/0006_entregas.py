"""Entregas de mensagem. E-mail agora; telefone reservado. Não apaga dado."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0006_entregas"
down_revision: str | None = "0005_biblioteca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _existe("entregas_mensagem"):
        return
    op.create_table(
        "entregas_mensagem",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canal", sa.String(16), nullable=False),
        sa.Column("destino", sa.String(255), nullable=False),
        sa.Column("assunto", sa.String(160), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("referencia", sa.String(40), nullable=False),
        sa.Column("projeto_id", sa.String(36), nullable=True),
        sa.Column("usuario_id", sa.String(36), nullable=True),
        sa.Column("erro", sa.String(160), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    if _existe("entregas_mensagem"):
        op.drop_table("entregas_mensagem")
