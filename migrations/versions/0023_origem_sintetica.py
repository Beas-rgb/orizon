"""Marcador de origem em organização e projeto (laboratório).

Aditivo. Dado existente fica NORMAL. Nenhuma tabela é apagada.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_origem_sintetica"
down_revision: str | None = "0022_envio_e_tarefas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizacoes",
        sa.Column(
            "origem",
            sa.String(16),
            nullable=False,
            server_default="NORMAL",
        ),
    )
    op.add_column(
        "projetos",
        sa.Column(
            "origem",
            sa.String(16),
            nullable=False,
            server_default="NORMAL",
        ),
    )


def downgrade() -> None:
    op.drop_column("projetos", "origem")
    op.drop_column("organizacoes", "origem")
