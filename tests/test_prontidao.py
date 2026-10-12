"""Readiness: schema na revisão esperada, tabelas presentes, R2 em produção."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.prontidao import revisao_esperada
from app.integrations import arquivos
from app.main import app


def _marcar_revisao(db, valor: str | None) -> None:
    db.execute(
        text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32))")
    )
    db.execute(text("DELETE FROM alembic_version"))
    if valor is not None:
        db.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
            {"v": valor},
        )
    db.commit()


def test_schema_sem_versao_fica_indisponivel(db) -> None:
    resposta = TestClient(app).get("/health/ready")
    assert resposta.status_code == 503
    assert resposta.json()["motivos"] == ["schema_sem_versao"]
    assert "usuarios" not in resposta.text


def test_revisao_esperada_fica_pronta(db) -> None:
    _marcar_revisao(db, revisao_esperada())
    resposta = TestClient(app).get("/health/ready")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_revisao_divergente_fica_indisponivel(db) -> None:
    _marcar_revisao(db, "0020_lab")
    resposta = TestClient(app).get("/health/ready")
    assert resposta.status_code == 503
    assert resposta.json()["motivos"] == ["revisao_divergente"]


def test_tabela_ausente_fica_indisponivel(db) -> None:
    _marcar_revisao(db, revisao_esperada())
    db.execute(text("DROP TABLE cenarios_lab"))
    db.commit()
    resposta = TestClient(app).get("/health/ready")
    assert resposta.status_code == 503
    assert resposta.json()["motivos"] == ["tabelas_ausentes"]
    assert "cenarios_lab" not in resposta.text


def test_banco_fora_nao_vaza_detalhe(monkeypatch) -> None:
    def quebrar():
        raise RuntimeError("postgresql://user:segredo@host/db recusou")

    monkeypatch.setattr("app.main.get_engine", quebrar)
    resposta = TestClient(app).get("/health/ready")
    assert resposta.status_code == 503
    assert resposta.json()["motivos"] == ["banco_indisponivel"]
    assert "segredo" not in resposta.text


def test_producao_sem_r2_fica_indisponivel(db, monkeypatch) -> None:
    _marcar_revisao(db, revisao_esperada())
    monkeypatch.setattr("app.core.config.settings.app_env", "production")
    monkeypatch.setattr("app.core.config.settings.r2_endpoint", "")
    resposta = TestClient(app).get("/health/ready")
    assert resposta.status_code == 503
    assert resposta.json()["motivos"] == ["armazenamento_ausente"]


def test_producao_sem_r2_nao_grava_em_disco(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.config.settings.app_env", "production")
    monkeypatch.setattr("app.core.config.settings.r2_endpoint", "")
    monkeypatch.setattr(arquivos, "RAIZ", tmp_path / "biblioteca")
    with pytest.raises(arquivos.ArquivoInvalido, match="Armazenamento"):
        arquivos.guardar("doc-1", b"conteudo de texto", "text/plain")
    assert not (tmp_path / "biblioteca").exists()


def test_desenvolvimento_sem_r2_usa_disco(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.config.settings.app_env", "development")
    monkeypatch.setattr("app.core.config.settings.r2_endpoint", "")
    monkeypatch.setattr(arquivos, "RAIZ", tmp_path / "biblioteca")
    chave, _resumo = arquivos.guardar("doc-1", b"conteudo de texto", "text/plain")
    assert (tmp_path / "biblioteca" / "doc-1").is_file()
    assert chave.endswith("doc-1")
