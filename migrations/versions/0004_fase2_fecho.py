"""Setores e configuração do projeto. IA nasce DESATIVADA. Não apaga dado."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0004_fase2_fecho"
down_revision: str | None = "0003_projetos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _existe("setores"):
        op.create_table(
            "setores",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("projeto_id", sa.String(36), nullable=False),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["projeto_id"], ["projetos.id"]),
        )
    if not _existe("configuracoes_projeto"):
        op.create_table(
            "configuracoes_projeto",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("projeto_id", sa.String(36), nullable=False),
            sa.Column(
                "pesquisas_habilitadas",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "ia_modo",
                sa.String(32),
                nullable=False,
                server_default="DESATIVADA",
            ),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["projeto_id"], ["projetos.id"]),
            sa.UniqueConstraint("projeto_id", name="uq_config_projeto"),
        )


def downgrade() -> None:
    for nome in ("configuracoes_projeto", "setores"):
        if _existe(nome):
            op.drop_table(nome)
