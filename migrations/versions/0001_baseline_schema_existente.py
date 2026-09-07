"""Baseline do schema já existente no Neon.

Não cria, altera nem apaga tabela. O banco já tem o desenho (21 tabelas).
Esta revisão só existe para o Alembic saber o ponto de partida.

`alembic stamp head` marca esta revisão como aplicada sem executar SQL.
`alembic upgrade head` também não muda nada, porque upgrade() está vazio.
"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    # Não há DDL para desfazer. O schema real do Neon permanece.
    pass
