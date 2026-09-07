from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_nao_exige_banco(monkeypatch) -> None:
    """Sem DATABASE_URL o /health continua 200. O banco não é pré-requisito."""
    monkeypatch.setattr("app.core.config.settings.database_url", "")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
