"""Guardas de segurança para a leitura da revisão Alembic no boot."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.migracao import _revisao_atual


def _url(tmp_path, nome: str = "schema.db") -> str:
    return f"sqlite:///{tmp_path / nome}"


def test_banco_vazio_pode_iniciar_a_cadeia_de_migracoes(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    engine.dispose()

    assert _revisao_atual(url) is None


def test_schema_existente_sem_alembic_version_bloqueia_boot(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(text("CREATE TABLE usuarios (id TEXT PRIMARY KEY)"))
    engine.dispose()

    with pytest.raises(RuntimeError, match="Migração automática bloqueada"):
        _revisao_atual(url)


def test_revisao_alembic_existente_e_retornada(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conexao.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0020_lab')")
        )
    engine.dispose()

    assert _revisao_atual(url) == "0020_lab"


def test_alembic_version_vazia_bloqueia_boot(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
    engine.dispose()

    with pytest.raises(RuntimeError, match="não contém uma revisão"):
        _revisao_atual(url)


def test_erro_de_conexao_nao_e_convertido_em_ausencia_de_revisao(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'diretorio-inexistente' / 'schema.db'}"

    with pytest.raises(SQLAlchemyError):
        _revisao_atual(url)
