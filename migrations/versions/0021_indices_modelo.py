"""Índices que os modelos já pedem com index=True.

Não altera 0001–0020. Não usa CREATE INDEX CONCURRENTLY: o upgrade
permanece na mesma transação.
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
    for nome, tabela, colunas in INDICES:
        op.create_index(nome, tabela, colunas)


def downgrade() -> None:
    for nome, tabela, _colunas in reversed(INDICES):
        op.drop_index(nome, table_name=tabela)
