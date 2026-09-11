import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.email import EmailNaoEnviado, caixa_email, modo_envio
from app.main import app


def test_health_email_local() -> None:
    resposta = TestClient(app).get("/health/email")
    assert resposta.status_code == 200
    assert resposta.json() == {"modo": "local"}
    assert "token" not in resposta.text.lower()


def test_health_email_mailtrap_nao_vaza_segredo(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailtrap_api_token", "token-de-teste")
    resposta = TestClient(app).get("/health/email")
    assert resposta.json() == {"modo": "mailtrap"}
    assert "token-de-teste" not in resposta.text


def test_modo_envio_prioriza_mailtrap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailtrap_api_token", "token-de-teste")
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.dev")
    monkeypatch.setattr(settings, "smtp_user", "user")
    monkeypatch.setattr(settings, "smtp_password", "senha")
    assert modo_envio() == "mailtrap"


def test_envia_pelo_sdk_mailtrap(monkeypatch) -> None:
    visto: dict[str, object] = {}

    class ClienteFalso:
        def __init__(self, token: str, **_kwargs) -> None:
            visto["tem_token"] = bool(token)
            visto["token_placeholder"] = token == "<YOUR_API_TOKEN>"

        def send(self, mail) -> dict[str, bool]:
            visto["destino"] = mail.to[0].email
            visto["remetente"] = mail.sender.email
            visto["nome"] = mail.sender.name
            visto["assunto"] = mail.subject
            visto["texto"] = mail.text
            visto["categoria"] = mail.category
            return {"success": True}

    monkeypatch.setattr(settings, "mailtrap_api_token", "token-de-teste")
    monkeypatch.setattr(settings, "mailtrap_from_email", "hello@demomailtrap.co")
    monkeypatch.setattr(settings, "mailtrap_from_name", "Horizon")
    monkeypatch.setattr("mailtrap.MailtrapClient", ClienteFalso)

    caixa_email.enviar(
        "destinatario@exemplo.dev",
        "Você é incrível!",
        "Parabéns pelo envio de teste.",
        categoria="Integration Test",
    )

    assert visto["tem_token"] is True
    assert visto["token_placeholder"] is False
    assert visto["destino"] == "destinatario@exemplo.dev"
    assert visto["remetente"] == "hello@demomailtrap.co"
    assert visto["nome"] == "Horizon"
    assert visto["assunto"] == "Você é incrível!"
    assert visto["texto"] == "Parabéns pelo envio de teste."
    assert visto["categoria"] == "Integration Test"
    assert caixa_email.mensagens[-1]["destino"] == "destinatario@exemplo.dev"


def test_mailtrap_sem_remetente_falha(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailtrap_api_token", "token-de-teste")
    monkeypatch.setattr(settings, "mailtrap_from_email", "")
    monkeypatch.setattr(settings, "smtp_from", "")
    with pytest.raises(EmailNaoEnviado):
        caixa_email.enviar("a@b.dev", "assunto", "corpo")


def test_sem_token_nao_chama_mailtrap(monkeypatch) -> None:
    chamado: list[str] = []

    class ClienteFalso:
        def __init__(self, token: str, **_kwargs) -> None:
            chamado.append(token)

        def send(self, mail) -> None:
            raise AssertionError("não deveria enviar")

    monkeypatch.setattr("mailtrap.MailtrapClient", ClienteFalso)
    caixa_email.enviar("a@b.dev", "assunto", "corpo")
    assert chamado == []
    assert caixa_email.mensagens[-1]["destino"] == "a@b.dev"
