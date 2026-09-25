"""Cargo e perfil do funcionário com hierarquia."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0014_estrutura_organizacional"
down_revision: str | None = "0013_entrega_provedor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tabelas() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tabelas = _tabelas()
    if "cargos" not in tabelas:
        op.create_table(
            "cargos",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("projeto_id", sa.String(36), sa.ForeignKey("projetos.id"), nullable=False),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("projeto_id", "nome", name="uq_cargo_projeto_nome"),
        )
        op.create_index("ix_cargos_projeto_id", "cargos", ["projeto_id"])
    if "perfis_funcionario" not in tabelas:
        op.create_table(
            "perfis_funcionario",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("projeto_id", sa.String(36), sa.ForeignKey("projetos.id"), nullable=False),
            sa.Column("usuario_id", sa.String(36), sa.ForeignKey("usuarios.id"), nullable=False),
            sa.Column("setor_id", sa.String(36), sa.ForeignKey("setores.id"), nullable=True),
            sa.Column("cargo_id", sa.String(36), sa.ForeignKey("cargos.id"), nullable=True),
            sa.Column("superior_id", sa.String(36), sa.ForeignKey("usuarios.id"), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "projeto_id",
                "usuario_id",
                name="uq_perfil_funcionario_projeto_usuario",
            ),
        )
        op.create_index(
            "ix_perfis_funcionario_projeto_id",
            "perfis_funcionario",
            ["projeto_id"],
        )
        op.create_index(
            "ix_perfis_funcionario_usuario_id",
            "perfis_funcionario",
            ["usuario_id"],
        )


def downgrade() -> None:
    tabelas = _tabelas()
    if "perfis_funcionario" in tabelas:
        op.drop_table("perfis_funcionario")
    if "cargos" in tabelas:
        op.drop_table("cargos")
