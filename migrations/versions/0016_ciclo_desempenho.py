"""Ciclo de avaliação e relações avaliador-avaliado."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0016_ciclo_desempenho"
down_revision: str | None = "0015_config_calculo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tabelas() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tabelas = _tabelas()
    if "ciclos_avaliacao" not in tabelas:
        op.create_table(
            "ciclos_avaliacao",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("projeto_id", sa.String(36), sa.ForeignKey("projetos.id"), nullable=False),
            sa.Column("nome", sa.String(200), nullable=False),
            sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("escopo", sa.String(32), nullable=False, server_default="ORGANIZACAO"),
            sa.Column("configuracao", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="RASCUNHO"),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_ciclos_avaliacao_projeto_id", "ciclos_avaliacao", ["projeto_id"])
    if "avaliacao_relacionamentos" not in tabelas:
        op.create_table(
            "avaliacao_relacionamentos",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("ciclo_id", sa.String(36), sa.ForeignKey("ciclos_avaliacao.id"), nullable=False),
            sa.Column("avaliador_id", sa.String(36), sa.ForeignKey("usuarios.id"), nullable=False),
            sa.Column("avaliado_id", sa.String(36), sa.ForeignKey("usuarios.id"), nullable=False),
            sa.Column("tipo_relacao", sa.String(32), nullable=False),
            sa.Column("perspectiva_id", sa.String(36), nullable=True),
            sa.Column("peso", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("status", sa.String(32), nullable=False, server_default="PENDENTE"),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "ciclo_id",
                "avaliador_id",
                "avaliado_id",
                "tipo_relacao",
                name="uq_avaliacao_relacionamento",
            ),
        )
        op.create_index(
            "ix_avaliacao_relacionamentos_ciclo_id",
            "avaliacao_relacionamentos",
            ["ciclo_id"],
        )
        op.create_index(
            "ix_avaliacao_relacionamentos_avaliador_id",
            "avaliacao_relacionamentos",
            ["avaliador_id"],
        )
        op.create_index(
            "ix_avaliacao_relacionamentos_avaliado_id",
            "avaliacao_relacionamentos",
            ["avaliado_id"],
        )


def downgrade() -> None:
    tabelas = _tabelas()
    if "avaliacao_relacionamentos" in tabelas:
        op.drop_table("avaliacao_relacionamentos")
    if "ciclos_avaliacao" in tabelas:
        op.drop_table("ciclos_avaliacao")
