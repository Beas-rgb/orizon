"""Colunas de midia em perguntas e template_perguntas.

Nao apaga dados. So ADD COLUMN se ainda nao existir.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0011_pergunta_midia"
down_revision: str | None = "0010_pesquisa_participantes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _colunas(tabela: str) -> set[str]:
    insp = inspect(op.get_bind())
    if tabela not in insp.get_table_names():
        return set()
    return {coluna["name"] for coluna in insp.get_columns(tabela)}


def upgrade() -> None:
    for tabela in ("perguntas", "template_perguntas"):
        cols = _colunas(tabela)
        if not cols:
            continue
        if "midia_tipo" not in cols:
            op.add_column(
                tabela,
                sa.Column("midia_tipo", sa.String(16), nullable=True),
            )
        if "midia_key" not in cols:
            op.add_column(
                tabela,
                sa.Column("midia_key", sa.String(500), nullable=True),
            )


def downgrade() -> None:
    for tabela in ("perguntas", "template_perguntas"):
        cols = _colunas(tabela)
        if "midia_key" in cols:
            op.drop_column(tabela, "midia_key")
        if "midia_tipo" in cols:
            op.drop_column(tabela, "midia_tipo")
