"""Índices quentes e drift. O drift completo só roda com Postgres."""

import os

import pytest

NOMES = (
    "ix_projeto_usuarios_usuario_id",
    "ix_sessoes_usuario_aberta",
    "ix_setores_projeto_id",
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL_PG"),
    reason="índice concorrente só é provado no Postgres",
)


def test_indices_quentes_existem() -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["TEST_DATABASE_URL_PG"])
    with engine.connect() as conexao:
        linhas = conexao.execute(
            text("select indexname from pg_indexes where indexname = any(:nomes)"),
            {"nomes": list(NOMES)},
        ).scalars()
        achados = set(linhas)
    assert achados == set(NOMES)


def test_sem_drift() -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from app.models import Base

    engine = create_engine(os.environ["TEST_DATABASE_URL_PG"])
    with engine.connect() as conexao:
        contexto = MigrationContext.configure(conexao)
        diferencas = compare_metadata(contexto, Base.metadata)
    assert diferencas == []
