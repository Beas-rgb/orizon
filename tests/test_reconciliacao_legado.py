"""Reconciliação do legado: só cópia isolada, nunca head sem equivalência."""

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.core import reconciliacao_legado as rec
from app.core.migracao import mapa_revisoes
from app.models.base import Base

OK = rec.CONFIRMACAO
HEAD = "0023_origem_sintetica"


def _url(tmp_path) -> str:
    return f"sqlite:///{tmp_path / 'copia.db'}"


def _modelos(url: str) -> None:
    import app.models  # noqa: F401

    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()


def _tabelas(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_head_do_teste_e_o_do_grafo() -> None:
    assert mapa_revisoes()[0] == HEAD


def test_schema_igual_aos_modelos_registra_head(tmp_path) -> None:
    url = _url(tmp_path)
    _modelos(url)
    relatorio = rec.registrar_head(url, OK, HEAD)
    assert relatorio.equivalente
    engine = create_engine(url)
    with engine.connect() as conexao:
        versoes = conexao.execute(text("select version_num from alembic_version"))
        assert versoes.scalars().all() == [HEAD]
    engine.dispose()


def test_tabela_legada_extra_bloqueia_e_fica_preservada(tmp_path) -> None:
    url = _url(tmp_path)
    _modelos(url)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(text("CREATE TABLE ia_conversas (id TEXT PRIMARY KEY)"))
        conexao.execute(text("INSERT INTO ia_conversas (id) VALUES ('c1')"))
    engine.dispose()

    relatorio = rec.inspecionar(url, OK)
    assert relatorio.tabelas_extras == ["ia_conversas"]
    with pytest.raises(rec.ReconciliacaoRecusada, match="diferente do head"):
        rec.registrar_head(url, OK, HEAD)
    assert "ia_conversas" in _tabelas(url)
    assert "alembic_version" not in _tabelas(url)


def test_coluna_legada_sem_regra_bloqueia(tmp_path) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text("CREATE TABLE usuarios (id TEXT PRIMARY KEY, nome_completo TEXT)")
        )
    engine.dispose()

    relatorio = rec.inspecionar(url, OK)
    assert "usuarios.nome_completo -> nome" in relatorio.sem_regra
    assert any(item.startswith("add_table ") for item in relatorio.divergencias)
    with pytest.raises(rec.ReconciliacaoRecusada):
        rec.registrar_head(url, OK, HEAD)
    assert _tabelas(url) == {"usuarios"}


def test_coluna_ausente_bloqueia(tmp_path) -> None:
    url = _url(tmp_path)
    _modelos(url)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(text("ALTER TABLE cenarios_lab DROP COLUMN erro"))
    engine.dispose()

    relatorio = rec.inspecionar(url, OK)
    assert "add_column cenarios_lab.erro" in relatorio.divergencias
    with pytest.raises(rec.ReconciliacaoRecusada):
        rec.registrar_head(url, OK, HEAD)


def test_banco_vazio_e_recusado(tmp_path) -> None:
    url = _url(tmp_path)
    create_engine(url).dispose()
    with pytest.raises(rec.ReconciliacaoRecusada, match="banco vazio"):
        rec.inspecionar(url, OK)


def test_banco_ja_versionado_e_recusado(tmp_path) -> None:
    url = _url(tmp_path)
    _modelos(url)
    rec.registrar_head(url, OK, HEAD)
    with pytest.raises(rec.ReconciliacaoRecusada, match="já existe"):
        rec.registrar_head(url, OK, HEAD)


@pytest.mark.parametrize(
    ("campo", "valor", "motivo"),
    [
        ("app_env", "production", "production"),
        ("confirmacao", "sim", "confirmação"),
        ("database_url", "MESMA", "banco da aplicação"),
    ],
)
def test_recusa_antes_de_conectar(monkeypatch, tmp_path, campo, valor, motivo) -> None:
    url = _url(tmp_path)
    confirmacao = OK
    if campo == "app_env":
        monkeypatch.setattr("app.core.config.settings.app_env", valor)
    elif campo == "confirmacao":
        confirmacao = valor
    else:
        monkeypatch.setattr("app.core.config.settings.database_url", url + "/")
    with pytest.raises(rec.ReconciliacaoRecusada, match=motivo):
        rec.inspecionar(url, confirmacao)
    assert not Path(tmp_path / "copia.db").exists()


def test_boot_nao_importa_reconciliacao() -> None:
    for caminho in ("app/core/migracao.py", "app/main.py", "Dockerfile"):
        assert "reconciliacao_legado" not in Path(caminho).read_text(encoding="utf-8")


PG_URL = os.environ.get("TEST_DATABASE_URL_PG", "").strip()


@pytest.fixture()
def banco_pg_temporario():
    if not PG_URL:
        pytest.skip("TEST_DATABASE_URL_PG ausente")
    nome = f"zz_recon_{uuid.uuid4().hex[:10]}"
    admin = create_engine(PG_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conexao:
        conexao.execute(text(f'CREATE DATABASE "{nome}"'))
    url = make_url(PG_URL).set(database=nome).render_as_string(hide_password=False)
    try:
        yield url
    finally:
        with admin.connect() as conexao:
            conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'))
        admin.dispose()


def test_postgres_modelos_equivalem_e_divergencia_bloqueia(banco_pg_temporario) -> None:
    url = banco_pg_temporario
    _modelos(url)
    assert rec.inspecionar(url, OK).equivalente

    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text("ALTER TABLE usuarios ALTER COLUMN ativo DROP DEFAULT")
        )
    engine.dispose()
    relatorio = rec.inspecionar(url, OK)
    assert "modify_default usuarios.ativo" in relatorio.divergencias
    with pytest.raises(rec.ReconciliacaoRecusada):
        rec.registrar_head(url, OK, HEAD)
    assert "alembic_version" not in _tabelas(url)
