"""Identidade: usuários, convite, recuperação e bloqueio de acesso.

Não apaga dado. Se a tabela já existir no Neon, só acrescenta as colunas
de força bruta quando faltarem. Não usa create_all.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0002_identidade"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def _colunas(nome: str) -> set[str]:
    return {col["name"] for col in inspect(op.get_bind()).get_columns(nome)}


def upgrade() -> None:
    if not _existe("usuarios"):
        op.create_table(
            "usuarios",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("nome", sa.String(160), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("senha_hash", sa.String(255), nullable=True),
            sa.Column("papel", sa.String(32), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "tentativas_falhas",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("bloqueado_ate", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("email", name="uq_usuarios_email"),
        )
    else:
        colunas = _colunas("usuarios")
        if "tentativas_falhas" not in colunas:
            op.add_column(
                "usuarios",
                sa.Column(
                    "tentativas_falhas",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                ),
            )
        if "bloqueado_ate" not in colunas:
            op.add_column(
                "usuarios",
                sa.Column("bloqueado_ate", sa.DateTime(timezone=True), nullable=True),
            )

    if not _existe("convites"):
        op.create_table(
            "convites",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("nome", sa.String(160), nullable=False),
            sa.Column("papel", sa.String(32), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("entrega", sa.String(32), nullable=False),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("aceito_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("convidado_por_id", sa.String(36), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["convidado_por_id"], ["usuarios.id"]),
            sa.UniqueConstraint("token_hash", name="uq_convites_token_hash"),
        )

    if not _existe("tokens_redefinicao"):
        op.create_table(
            "tokens_redefinicao",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("usuario_id", sa.String(36), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
            sa.UniqueConstraint("token_hash", name="uq_tokens_redefinicao_hash"),
        )

    if not _existe("controle_acesso"):
        op.create_table(
            "controle_acesso",
            sa.Column("chave", sa.String(280), primary_key=True),
            sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("bloqueado_ate", sa.DateTime(timezone=True), nullable=True),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        )

    if not _existe("sessoes"):
        op.create_table(
            "sessoes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("usuario_id", sa.String(36), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
            sa.UniqueConstraint("token_hash", name="uq_sessoes_token_hash"),
        )

    if not _existe("logs_auditoria"):
        op.create_table(
            "logs_auditoria",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("usuario_id", sa.String(36), nullable=True),
            sa.Column("acao", sa.String(64), nullable=False),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        )


def downgrade() -> None:
    # Não apaga usuarios, convites nem logs_auditoria: podem já ter dado no Neon.
    for nome in ("sessoes", "controle_acesso", "tokens_redefinicao"):
        if _existe(nome):
            op.drop_table(nome)
