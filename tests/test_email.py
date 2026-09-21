import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.email import (
    EmailNaoEnviado,
    ResultadoEmail,
    caixa_email,
    modo_envio,
)
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


def test_modo_envio_prioriza_sendgrid(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sendgrid_api_key", "SG.teste")
    monkeypatch.setattr(settings, "mailtrap_api_token", "token-de-teste")
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.dev")
    monkeypatch.setattr(settings, "smtp_user", "user")
    monkeypatch.setattr(settings, "smtp_password", "senha")
    assert modo_envio() == "sendgrid"


def test_modo_envio_prioriza_mailtrap_sobre_smtp(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sendgrid_api_key", "")
    monkeypatch.setattr(settings, "mailtrap_api_token", "token-de-teste")
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.dev")
    monkeypatch.setattr(settings, "smtp_user", "user")
    monkeypatch.setattr(settings, "smtp_password", "senha")
    assert modo_envio() == "mailtrap"


def test_envia_pelo_sendgrid(monkeypatch) -> None:
    visto: dict[str, object] = {}

    class RespostaFalsa:
        status = 202
        headers = {"X-Message-Id": "sg-message-123"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen_falso(pedido, timeout=20):
        visto["url"] = pedido.full_url
        visto["auth"] = pedido.get_header("Authorization")
        corpo = json.loads(pedido.data.decode("utf-8"))
        visto["destino"] = corpo["personalizations"][0]["to"][0]["email"]
        visto["remetente"] = corpo["from"]["email"]
        visto["nome"] = corpo["from"]["name"]
        visto["assunto"] = corpo["subject"]
        visto["texto"] = corpo["content"][0]["value"]
        visto["html"] = corpo["content"][1]["value"]
        visto["categories"] = corpo.get("categories")
        visto["custom_args"] = corpo["personalizations"][0].get("custom_args")
        visto["click_tracking"] = corpo["tracking_settings"]["click_tracking"][
            "enable"
        ]
        return RespostaFalsa()

    monkeypatch.setattr(settings, "sendgrid_api_key", "SG.teste")
    monkeypatch.setattr(settings, "sendgrid_from_email", "noreply@orizon.dev")
    monkeypatch.setattr(settings, "sendgrid_from_name", "Horizon")
    monkeypatch.setattr("urllib.request.urlopen", urlopen_falso)

    resultado = caixa_email.enviar(
        "destinatario@exemplo.dev",
        "Você é incrível!",
        "Parabéns pelo envio de teste.\nhttps://orizon-api.onrender.com/app/primeiro-acesso?t=abc",
        categoria="CONVITE",
    )

    assert visto["url"] == "https://api.sendgrid.com/v3/mail/send"
    assert visto["auth"] == "Bearer SG.teste"
    assert visto["destino"] == "destinatario@exemplo.dev"
    assert visto["remetente"] == "noreply@orizon.dev"
    assert visto["nome"] == "Horizon"
    assert visto["assunto"] == "Você é incrível!"
    assert visto["categories"] == ["CONVITE"]
    assert visto["custom_args"] is None
    assert visto["click_tracking"] is False
    assert resultado == ResultadoEmail("sendgrid", "sg-message-123")
    assert "Parabéns pelo envio de teste." in str(visto["texto"])
    link_html = (
        '<a href="https://orizon-api.onrender.com/'
        'app/primeiro-acesso?t=abc">'
    )
    assert link_html in str(visto["html"])


def test_destino_recebe_email_real() -> None:
    from app.integrations.email import destino_recebe_email_real

    assert destino_recebe_email_real("joao951biel@gmail.com") is True
    assert destino_recebe_email_real("joao.gabriel@horizon.local") is False
    assert destino_recebe_email_real("a@localhost") is False
    assert destino_recebe_email_real("invalido") is False

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
    monkeypatch.setattr(settings, "sendgrid_api_key", "")
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
    monkeypatch.setattr(settings, "sendgrid_api_key", "")
    monkeypatch.setattr(settings, "mailtrap_api_token", "token-de-teste")
    monkeypatch.setattr(settings, "mailtrap_from_email", "")
    monkeypatch.setattr(settings, "smtp_from", "")
    with pytest.raises(EmailNaoEnviado):
        caixa_email.enviar("a@b.dev", "assunto", "corpo")


def test_fallback_mailtrap_quando_sendgrid_falha(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sendgrid_api_key", "SG.invalida")
    monkeypatch.setattr(settings, "mailtrap_api_token", "mt-valido")
    monkeypatch.setattr(
        "app.integrations.email._enviar_sendgrid",
        lambda *a, **k: (_ for _ in ()).throw(
            EmailNaoEnviado("SendGrid indisponível")
        ),
    )
    monkeypatch.setattr(
        "app.integrations.email._enviar_mailtrap",
        lambda *a, **k: ResultadoEmail("mailtrap", "mt-123"),
    )

    resultado = caixa_email.enviar("a@b.dev", "assunto", "corpo")

    assert resultado == ResultadoEmail("mailtrap", "mt-123")


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


def test_erro_entrega_seguro_nao_vaza_segredo() -> None:
    from app.services.notificacao import _erro_entrega_seguro

    msg = _erro_entrega_seguro(Exception("Unauthorized invalid token Bearer abc"))
    assert "token ou permissão" in msg
    assert "Bearer" not in msg
    dominio = _erro_entrega_seguro(Exception("Sender domain not verified"))
    assert "domínio" in dominio.lower() or "remetente" in dominio.lower()
    limpo = _erro_entrega_seguro(Exception("password=segredo postgres://x"))
    assert "segredo" not in limpo
    assert "postgres" not in limpo.lower()
    rede = _erro_entrega_seguro(Exception("[Errno 101] Network is unreachable"))
    assert "SendGrid" in rede
    assert "587" in rede
