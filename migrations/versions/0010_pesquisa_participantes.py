"""Participantes da pesquisa: 1 funcionario por pesquisa (UNIQUE).

Nao apaga dados. So CREATE TABLE se ainda nao existir.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0010_pesquisa_participantes"
down_revision: str | None = "0009_pesquisas_notificacoes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _existe("pesquisa_participantes"):
        return
    op.create_table(
        "pesquisa_participantes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "pesquisa_id",
            sa.String(36),
            sa.ForeignKey("pesquisas.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "usuario_id",
            sa.String(36),
            sa.ForeignKey("usuarios.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDENTE"),
        sa.Column(
            "token_id",
            sa.String(36),
            sa.ForeignKey("tokens_resposta.id"),
            nullable=True,
        ),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("respondido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "pesquisa_id",
            "usuario_id",
            name="uq_pesquisa_participante",
        ),
    )


def downgrade() -> None:
    if _existe("pesquisa_participantes"):
        op.drop_table("pesquisa_participantes")
