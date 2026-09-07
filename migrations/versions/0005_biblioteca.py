"""Biblioteca. Visibilidade padrão PRIVADO. Não apaga dado."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0005_biblioteca"
down_revision: str | None = "0004_fase2_fecho"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _existe("documentos"):
        return
    op.create_table(
        "documentos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("consultor_id", sa.String(36), nullable=False),
        sa.Column("projeto_id", sa.String(36), nullable=True),
        sa.Column("camada", sa.String(32), nullable=False),
        sa.Column(
            "visibilidade",
            sa.String(32),
            nullable=False,
            server_default="PRIVADO",
        ),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("mime", sa.String(120), nullable=False),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("armazenamento_key", sa.String(255), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["consultor_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["projeto_id"], ["projetos.id"]),
    )


def downgrade() -> None:
    if _existe("documentos"):
        op.drop_table("documentos")
