"""Hash em tokens_resposta + índices de desempenho (P1.1 / P1.7)."""

from alembic import op
import sqlalchemy as sa

revision = "0012_token_hash_indices"
down_revision = "0011_pergunta_midia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # token em claro (36) → hash SHA-256 (64). Dados demo/legado inválidos
    # após o deploy; gerar novos links.
    with op.batch_alter_table("tokens_resposta") as batch:
        batch.alter_column(
            "token",
            new_column_name="token_hash",
            existing_type=sa.String(length=36),
            type_=sa.String(length=64),
            existing_nullable=False,
        )

    op.create_index(
        "ix_respostas_pergunta_id",
        "respostas",
        ["pergunta_id"],
        unique=False,
    )
    op.create_index(
        "ix_respostas_opcao_id",
        "respostas",
        ["opcao_id"],
        unique=False,
    )
    op.create_index(
        "ix_projetos_consultor_id",
        "projetos",
        ["consultor_id"],
        unique=False,
    )
    op.create_index(
        "ix_pesquisas_projeto_status",
        "pesquisas",
        ["projeto_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pesquisas_projeto_status", table_name="pesquisas")
    op.drop_index("ix_projetos_consultor_id", table_name="projetos")
    op.drop_index("ix_respostas_opcao_id", table_name="respostas")
    op.drop_index("ix_respostas_pergunta_id", table_name="respostas")
    with op.batch_alter_table("tokens_resposta") as batch:
        batch.alter_column(
            "token_hash",
            new_column_name="token",
            existing_type=sa.String(length=64),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
