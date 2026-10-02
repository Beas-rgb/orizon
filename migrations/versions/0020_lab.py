"""Laboratório: cenários sintéticos para o consultor de teste."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_lab"
down_revision: str | None = "0019_indice_superior"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column(
            "tipo_conta",
            sa.String(16),
            nullable=False,
            server_default="NORMAL",
        ),
    )
    op.create_check_constraint(
        "ck_usuarios_tipo_conta",
        "usuarios",
        "tipo_conta IN ('NORMAL', 'TESTE', 'SINTETICO')",
    )
    op.create_table(
        "cenarios_lab",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "dono_id",
            sa.String(36),
            sa.ForeignKey("usuarios.id"),
            nullable=False,
        ),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("tipo", sa.String(32), nullable=False),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("perfil", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "projeto_id",
            sa.String(36),
            sa.ForeignKey("projetos.id"),
            nullable=True,
        ),
        sa.Column(
            "progresso",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
    op.create_index("ix_cenarios_lab_dono_id", "cenarios_lab", ["dono_id"])


def downgrade() -> None:
    op.drop_index("ix_cenarios_lab_dono_id", table_name="cenarios_lab")
    op.drop_table("cenarios_lab")
    op.drop_constraint("ck_usuarios_tipo_conta", "usuarios", type_="check")
    op.drop_column("usuarios", "tipo_conta")
