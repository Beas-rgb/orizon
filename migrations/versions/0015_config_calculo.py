"""Configuração de cálculo da pesquisa (JSON estruturado)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0015_config_calculo"
down_revision: str | None = "0014_estrutura_organizacional"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _colunas() -> set[str]:
    return {
        coluna["name"]
        for coluna in inspect(op.get_bind()).get_columns("pesquisas")
    }


def upgrade() -> None:
    colunas = _colunas()
    with op.batch_alter_table("pesquisas") as batch:
        if "config_calculo" not in colunas:
            batch.add_column(sa.Column("config_calculo", sa.Text(), nullable=True))


def downgrade() -> None:
    colunas = _colunas()
    with op.batch_alter_table("pesquisas") as batch:
        if "config_calculo" in colunas:
            batch.drop_column("config_calculo")
