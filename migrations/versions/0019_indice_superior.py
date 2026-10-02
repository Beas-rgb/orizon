"""Índice dos filhos vivos. A árvore grande pede um superior de cada vez."""

from collections.abc import Sequence

from alembic import op

revision: str = "0019_indice_superior"
down_revision: str | None = "0018_indices_quentes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        op.create_index(
            "ix_perfis_funcionario_superior_vivo",
            "perfis_funcionario",
            ["superior_id"],
        )
        return
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_perfis_funcionario_superior_vivo "
            "ON perfis_funcionario (superior_id) WHERE deleted_at IS NULL"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS "
                "ix_perfis_funcionario_superior_vivo"
            )
        return
    op.drop_index(
        "ix_perfis_funcionario_superior_vivo",
        table_name="perfis_funcionario",
    )
