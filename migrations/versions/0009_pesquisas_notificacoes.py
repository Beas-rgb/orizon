"""Tabelas de pesquisa, templates e notificacoes faltantes no Neon.

O baseline assumiu 21 tabelas, mas pesquisas/notificacoes nunca entraram
via Alembic. Sem isto, GET/POST /projetos/.../pesquisas devolve 500.
Nao apaga nem altera dado existente — so CREATE TABLE se nao existir.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0009_pesquisas_notificacoes"
down_revision: str | None = "0008_pedidos_consultora"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _existe("pesquisas"):
        op.create_table(
            "pesquisas",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("projeto_id", sa.String(36), nullable=False, index=True),
            sa.Column("criado_por", sa.String(36), nullable=False),
            sa.Column("titulo", sa.String(200), nullable=False),
            sa.Column("descricao", sa.Text, nullable=True),
            sa.Column("tipo", sa.String(40), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("bloqueada", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("publicada_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("encerrada_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("disponivel_de", sa.DateTime(timezone=True), nullable=True),
            sa.Column("disponivel_ate", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("template_origem_id", sa.String(36), nullable=True),
        )

    if not _existe("perguntas"):
        op.create_table(
            "perguntas",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "pesquisa_id",
                sa.String(36),
                sa.ForeignKey("pesquisas.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("texto", sa.Text, nullable=False),
            sa.Column("tipo", sa.String(40), nullable=False),
            sa.Column("obrigatoria", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("ordem", sa.SmallInteger, nullable=False, server_default="1"),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _existe("opcoes_resposta"):
        op.create_table(
            "opcoes_resposta",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "pergunta_id",
                sa.String(36),
                sa.ForeignKey("perguntas.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("texto", sa.String(200), nullable=False),
            sa.Column("ordem", sa.SmallInteger, nullable=False, server_default="1"),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        )

    if not _existe("tokens_resposta"):
        op.create_table(
            "tokens_resposta",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "pesquisa_id",
                sa.String(36),
                sa.ForeignKey("pesquisas.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("setor_id", sa.String(36), nullable=True),
            sa.Column("token", sa.String(36), nullable=False, unique=True),
            sa.Column("usado", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        )

    if not _existe("respostas"):
        op.create_table(
            "respostas",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "token_id",
                sa.String(36),
                sa.ForeignKey("tokens_resposta.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "pergunta_id",
                sa.String(36),
                sa.ForeignKey("perguntas.id"),
                nullable=False,
            ),
            sa.Column("valor_texto", sa.Text, nullable=True),
            sa.Column("valor_numerico", sa.SmallInteger, nullable=True),
            sa.Column("opcao_id", sa.String(36), nullable=True),
            sa.Column("respondido_em", sa.DateTime(timezone=True), nullable=False),
        )

    if not _existe("templates_pesquisa"):
        op.create_table(
            "templates_pesquisa",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("criado_por", sa.String(36), nullable=False),
            sa.Column("nome", sa.String(200), nullable=False),
            sa.Column("descricao", sa.Text, nullable=True),
            sa.Column("tipo", sa.String(40), nullable=False),
            sa.Column("categoria", sa.String(32), nullable=False, server_default="generico"),
            sa.Column("compartilhado", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("versao", sa.SmallInteger, nullable=False, server_default="1"),
            sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("organizacao_id", sa.String(36), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _existe("template_perguntas"):
        op.create_table(
            "template_perguntas",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("template_id", sa.String(36), nullable=False, index=True),
            sa.Column("texto", sa.Text, nullable=False),
            sa.Column("tipo", sa.String(40), nullable=False),
            sa.Column("obrigatoria", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("ordem", sa.SmallInteger, nullable=False, server_default="1"),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _existe("template_opcoes_resposta"):
        op.create_table(
            "template_opcoes_resposta",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("pergunta_template_id", sa.String(36), nullable=False, index=True),
            sa.Column("texto", sa.String(200), nullable=False),
            sa.Column("ordem", sa.SmallInteger, nullable=False, server_default="1"),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _existe("notificacoes"):
        op.create_table(
            "notificacoes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "usuario_id",
                sa.String(36),
                sa.ForeignKey("usuarios.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("projeto_id", sa.String(36), nullable=True),
            sa.Column("tipo", sa.String(32), nullable=False),
            sa.Column("titulo", sa.String(160), nullable=False),
            sa.Column("mensagem", sa.Text, nullable=False),
            sa.Column("lida", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("lida_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("prioridade", sa.String(16), nullable=False, server_default="normal"),
        )


def downgrade() -> None:
    # Ordem inversa por FKs. So remove se existir.
    for tabela in (
        "notificacoes",
        "template_opcoes_resposta",
        "template_perguntas",
        "templates_pesquisa",
        "respostas",
        "tokens_resposta",
        "opcoes_resposta",
        "perguntas",
        "pesquisas",
    ):
        if _existe(tabela):
            op.drop_table(tabela)
