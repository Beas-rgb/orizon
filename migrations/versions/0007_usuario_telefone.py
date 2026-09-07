"""Coluna telefone em usuarios. Não apaga dado.

O modelo já grava telefone no cadastro. A migration de identidade
não criava essa coluna quando montava a tabela do zero.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0007_usuario_telefone"
down_revision: str | None = "0006_entregas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _colunas(nome: str) -> set[str]:
    return {col["name"] for col in inspect(op.get_bind()).get_columns(nome)}


def upgrade() -> None:
    if "telefone" not in _colunas("usuarios"):
        op.add_column("usuarios", sa.Column("telefone", sa.String(20), nullable=True))


def downgrade() -> None:
    if "telefone" in _colunas("usuarios"):
        op.drop_column("usuarios", "telefone")
