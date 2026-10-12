"""Timeouts por transação. Só no PostgreSQL de teste."""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.database import aplicar_timeouts

PG_URL = os.environ.get("TEST_DATABASE_URL_PG", "").strip()


def test_sqlite_ignora_timeouts() -> None:
    engine = create_engine("sqlite://")
    aplicar_timeouts(engine, 100, 100)
    with engine.begin() as conexao:
        assert conexao.execute(text("select 1")).scalar() == 1
    engine.dispose()


@pytest.mark.skipif(not PG_URL, reason="TEST_DATABASE_URL_PG ausente")
def test_statement_timeout_corta_a_consulta_longa() -> None:
    engine = create_engine(PG_URL)
    aplicar_timeouts(engine, 200, 100)
    try:
        with pytest.raises(OperationalError, match="statement timeout"):
            with engine.begin() as conexao:
                conexao.execute(text("select pg_sleep(1)"))
        with engine.begin() as conexao:
            valor = conexao.execute(text("show statement_timeout")).scalar()
            assert valor == "200ms"
            assert conexao.execute(text("show lock_timeout")).scalar() == "100ms"
    finally:
        engine.dispose()


@pytest.mark.skipif(not PG_URL, reason="TEST_DATABASE_URL_PG ausente")
def test_zero_nao_instala_limite() -> None:
    engine = create_engine(PG_URL)
    aplicar_timeouts(engine, 0, 0)
    try:
        with engine.begin() as conexao:
            assert conexao.execute(text("show statement_timeout")).scalar() == "0"
    finally:
        engine.dispose()
