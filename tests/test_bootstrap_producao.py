"""P0.1: bootstrap não existe em produção."""

from app.core.config import settings


def test_bootstrap_em_producao_retorna_404(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    resp = client.post(
        "/auth/bootstrap",
        json={
            "nome": "TI Invasor",
            "email": "invasor@orizon.local",
            "senha": "Senha-segura1!",
        },
    )
    assert resp.status_code == 404


def test_bootstrap_em_development_ainda_funciona(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "development")
    resp = client.post(
        "/auth/bootstrap",
        json={
            "nome": "TI Local",
            "email": "ti-local@orizon.local",
            "senha": "Senha-segura1!",
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
