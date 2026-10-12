"""Índices que os modelos já pedem com index=True.

Não altera 0001–0020. No PostgreSQL usa CREATE INDEX CONCURRENTLY fora de
transação, como a 0018: não bloqueia escrita nas tabelas.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021_indices_modelo"
down_revision: str | None = "0020_lab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDICES = (
    ("ix_convites_email", "convites", ["email"]),
    ("ix_documentos_consultor_id", "documentos", ["consultor_id"]),
    ("ix_documentos_projeto_id", "documentos", ["projeto_id"]),
    ("ix_pedidos_consultora_email", "pedidos_consultora", ["email"]),
    ("ix_projeto_usuarios_projeto_id", "projeto_usuarios", ["projeto_id"]),
    ("ix_tokens_redefinicao_usuario_id", "tokens_redefinicao", ["usuario_id"]),
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        for nome, tabela, colunas in INDICES:
            op.create_index(nome, tabela, colunas)
        return
    with op.get_context().autocommit_block():
        for nome, tabela, colunas in INDICES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {nome} "
                f"ON {tabela} ({', '.join(colunas)})"
            )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        for nome, tabela, _colunas in reversed(INDICES):
            op.drop_index(nome, table_name=tabela)
        return
    with op.get_context().autocommit_block():
        for nome, _tabela, _colunas in reversed(INDICES):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {nome}")
