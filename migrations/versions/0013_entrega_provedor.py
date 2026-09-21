"""Provedor e ID técnico das entregas de e-mail."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0013_entrega_provedor"
down_revision: str | None = "0012_token_hash_indices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _colunas() -> set[str]:
    return {
        coluna["name"]
        for coluna in inspect(op.get_bind()).get_columns("entregas_mensagem")
    }


def upgrade() -> None:
    colunas = _colunas()
    with op.batch_alter_table("entregas_mensagem") as batch:
        if "provedor" not in colunas:
            batch.add_column(sa.Column("provedor", sa.String(32), nullable=True))
        if "provedor_mensagem_id" not in colunas:
            batch.add_column(
                sa.Column("provedor_mensagem_id", sa.String(160), nullable=True)
            )


def downgrade() -> None:
    colunas = _colunas()
    with op.batch_alter_table("entregas_mensagem") as batch:
        if "provedor_mensagem_id" in colunas:
            batch.drop_column("provedor_mensagem_id")
        if "provedor" in colunas:
            batch.drop_column("provedor")
