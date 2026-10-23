"""CLIMA: tira o horário individual já gravado.

O downgrade não recupera o instante de cada envio. Isso é de propósito.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024_clima_sem_horario"
down_revision: str | None = "0023_origem_sintetica"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from app.services.pesquisa.horario_clima import limpar_horarios_clima

    limpar_horarios_clima(op.get_bind())


def downgrade() -> None:
    # O horário de cada envio foi apagado. Não há o que devolver.
    pass
