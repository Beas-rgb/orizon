"""Índices das consultas que já existem. Criados fora de transação no Postgres."""

from collections.abc import Sequence

from alembic import op

revision: str = "0018_indices_quentes"
down_revision: str | None = "0017_avaliacao_resposta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        op.create_index(
            "ix_projeto_usuarios_usuario_id",
            "projeto_usuarios",
            ["usuario_id"],
        )
        op.create_index("ix_sessoes_usuario_aberta", "sessoes", ["usuario_id"])
        op.create_index("ix_setores_projeto_id", "setores", ["projeto_id"])
        return
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_projeto_usuarios_usuario_id ON projeto_usuarios (usuario_id)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_sessoes_usuario_aberta ON sessoes (usuario_id) "
            "WHERE revogado_em IS NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
            "ix_setores_projeto_id ON setores (projeto_id)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_setores_projeto_id")
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS ix_sessoes_usuario_aberta"
            )
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS ix_projeto_usuarios_usuario_id"
            )
        return
    op.drop_index("ix_setores_projeto_id", table_name="setores")
    op.drop_index("ix_sessoes_usuario_aberta", table_name="sessoes")
    op.drop_index("ix_projeto_usuarios_usuario_id", table_name="projeto_usuarios")
