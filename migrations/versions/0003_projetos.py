"""Projetos, órgão por CNPJ e rótulos da lista.

Não apaga dado. Convite ganha projeto_id se a coluna não existir.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0003_projetos"
down_revision: str | None = "0002_identidade"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROTULOS = (
    ("CLIMA", "Clima organizacional", 1),
    ("DESEMPENHO", "Desempenho", 2),
    ("CARGOS_SALARIOS", "Cargos e salários", 3),
    ("PERSONALIZADA", "Personalizada", 4),
)


def _existe(nome: str) -> bool:
    return nome in inspect(op.get_bind()).get_table_names()


def _colunas(nome: str) -> set[str]:
    return {col["name"] for col in inspect(op.get_bind()).get_columns(nome)}


def upgrade() -> None:
    if not _existe("organizacoes"):
        op.create_table(
            "organizacoes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("cnpj", sa.String(14), nullable=False),
            sa.Column("razao_social", sa.String(200), nullable=False),
            sa.Column("nome_fantasia", sa.String(200), nullable=True),
            sa.Column("municipio", sa.String(120), nullable=True),
            sa.Column("uf", sa.String(2), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("cnpj", name="uq_organizacoes_cnpj"),
        )
    if not _existe("rotulos_projeto"):
        op.create_table(
            "rotulos_projeto",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("codigo", sa.String(40), nullable=False),
            sa.Column("nome", sa.String(80), nullable=False),
            sa.Column("ordem", sa.Integer(), nullable=False),
            sa.UniqueConstraint("codigo", name="uq_rotulos_projeto_codigo"),
        )
    if not _existe("projetos"):
        op.create_table(
            "projetos",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("organizacao_id", sa.String(36), nullable=False),
            sa.Column("consultor_id", sa.String(36), nullable=False),
            sa.Column("rotulo_id", sa.String(36), nullable=False),
            sa.Column("estado", sa.String(32), nullable=False),
            sa.Column("vinculo_tipo", sa.String(32), nullable=False),
            sa.Column("vinculo_titulo", sa.String(200), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["organizacao_id"], ["organizacoes.id"]),
            sa.ForeignKeyConstraint(["consultor_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["rotulo_id"], ["rotulos_projeto.id"]),
        )
    if not _existe("projeto_usuarios"):
        op.create_table(
            "projeto_usuarios",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("projeto_id", sa.String(36), nullable=False),
            sa.Column("usuario_id", sa.String(36), nullable=False),
            sa.Column("papel", sa.String(32), nullable=False),
            sa.ForeignKeyConstraint(["projeto_id"], ["projetos.id"]),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
            sa.UniqueConstraint(
                "projeto_id",
                "usuario_id",
                name="uq_projeto_usuario",
            ),
        )
    if _existe("convites") and "projeto_id" not in _colunas("convites"):
        op.add_column("convites", sa.Column("projeto_id", sa.String(36), nullable=True))
        op.create_foreign_key(
            "fk_convites_projeto_id",
            "convites",
            "projetos",
            ["projeto_id"],
            ["id"],
        )

    if _existe("rotulos_projeto"):
        for codigo, nome, ordem in ROTULOS:
            op.execute(
                sa.text(
                    "INSERT INTO rotulos_projeto (id, codigo, nome, ordem) "
                    "SELECT :id, :codigo, :nome, :ordem "
                    "WHERE NOT EXISTS ("
                    "SELECT 1 FROM rotulos_projeto WHERE codigo = :codigo"
                    ")"
                ).bindparams(
                    id=f"rotulo-{codigo.lower()}",
                    codigo=codigo,
                    nome=nome,
                    ordem=ordem,
                )
            )


def downgrade() -> None:
    if _existe("convites") and "projeto_id" in _colunas("convites"):
        op.drop_constraint("fk_convites_projeto_id", "convites", type_="foreignkey")
        op.drop_column("convites", "projeto_id")
    for nome in ("projeto_usuarios", "projetos", "rotulos_projeto", "organizacoes"):
        if _existe(nome):
            op.drop_table(nome)
