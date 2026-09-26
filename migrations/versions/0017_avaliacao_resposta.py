"""Resposta da avaliação ligada à relação, não ao token da pesquisa."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0017_avaliacao_resposta"
down_revision: str | None = "0016_ciclo_desempenho"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tabelas() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "avaliacao_respostas" in _tabelas():
        return
    op.create_table(
        "avaliacao_respostas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "relacionamento_id",
            sa.String(36),
            sa.ForeignKey("avaliacao_relacionamentos.id"),
            nullable=False,
        ),
        sa.Column(
            "pergunta_id",
            sa.String(36),
            sa.ForeignKey("perguntas.id"),
            nullable=False,
        ),
        sa.Column("valor_numerico", sa.SmallInteger(), nullable=True),
        sa.Column("valor_texto", sa.Text(), nullable=True),
        sa.Column("opcao_id", sa.String(36), nullable=True),
        sa.Column("respondido_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "relacionamento_id",
            "pergunta_id",
            name="uq_avaliacao_resposta_relacao_pergunta",
        ),
    )
    op.create_index(
        "ix_avaliacao_respostas_relacionamento_id",
        "avaliacao_respostas",
        ["relacionamento_id"],
    )
    op.create_index(
        "ix_avaliacao_respostas_pergunta_id",
        "avaliacao_respostas",
        ["pergunta_id"],
    )


def downgrade() -> None:
    if "avaliacao_respostas" in _tabelas():
        op.drop_table("avaliacao_respostas")
