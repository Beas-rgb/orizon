from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_db_sem_url_retorna_503(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.database_url", "")
    monkeypatch.setattr("app.core.database._engine", None)
    monkeypatch.setattr("app.core.database.SessionLocal", None)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["detail"] == "banco indisponível"
    assert "password" not in response.text.lower()


def test_health_db_select_1_ok(monkeypatch) -> None:
    def fake_check_db() -> None:
        return None

    monkeypatch.setattr("app.main.check_db", fake_check_db)

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_falha_nao_vaza_detalhe(monkeypatch) -> None:
    def fake_check_db() -> None:
        raise RuntimeError("postgresql://user:segredo@host/db connection refused")

    monkeypatch.setattr("app.main.check_db", fake_check_db)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert "segredo" not in response.text
    assert "postgresql://" not in response.text
