"""Chave de envio idempotente e tabela de tarefas longas.

Aditiva: uma coluna nula e uma tabela nova. Não reescreve dado existente.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_envio_e_tarefas"
down_revision: str | None = "0021_indices_modelo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pesquisa_participantes",
        sa.Column("envio_chave_hash", sa.String(64), nullable=True),
    )
    op.create_table(
        "tarefas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "dono_id",
            sa.String(36),
            sa.ForeignKey("usuarios.id"),
            nullable=False,
        ),
        sa.Column(
            "projeto_id",
            sa.String(36),
            sa.ForeignKey("projetos.id"),
            nullable=True,
        ),
        sa.Column("tipo", sa.String(32), nullable=False),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="PENDENTE"
        ),
        sa.Column("feito", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("falhas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erro", sa.String(160), nullable=True),
        sa.Column("resumo", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tarefas_dono_id", "tarefas", ["dono_id"])


def downgrade() -> None:
    op.drop_index("ix_tarefas_dono_id", table_name="tarefas")
    op.drop_table("tarefas")
    op.drop_column("pesquisa_participantes", "envio_chave_hash")
