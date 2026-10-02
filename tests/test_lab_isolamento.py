"""Isolamento de sintéticos e bloqueio de e-mail."""

from unittest.mock import MagicMock

import pytest

from app.integrations.email import EmailNaoEnviado, caixa_email, destino_sintetico
from app.models.usuario import Usuario
from app.services.notificacao import entregar_email
from scripts.criar_consultor_teste import criar_consultor_teste
from tests.contas import SENHA, abrir_dev


def test_destino_invalid_bloqueado() -> None:
    assert destino_sintetico("s1.abc@sintetico.invalid") is True
    assert destino_sintetico("pessoa@empresa.gov.br") is False


def test_enviar_sintetico_nao_chama_provedor(monkeypatch) -> None:
    remoto = MagicMock()
    monkeypatch.setattr(
        "app.integrations.email._enviar_sendgrid",
        remoto,
    )
    monkeypatch.setattr(
        "app.integrations.email.settings.sendgrid_api_key",
        "sg-fake",
    )
    with pytest.raises(EmailNaoEnviado, match="sintético"):
        caixa_email.enviar(
            "s0.abcd1234@sintetico.invalid",
            "x",
            "y",
        )
    remoto.assert_not_called()


def test_entregar_email_marca_falha_sem_rede(db, monkeypatch) -> None:
    enviado = MagicMock()
    monkeypatch.setattr(
        "app.services.notificacao.caixa_email.enviar",
        enviado,
    )
    entrega = entregar_email(
        db,
        "s1.xxxx@sintetico.invalid",
        "assunto",
        "corpo",
        "TESTE",
    )
    assert entrega.status == "FALHA"
    assert "sintético" in (entrega.erro or "").lower()
    enviado.assert_not_called()


def test_ti_nao_lista_consultor_teste(client, db) -> None:
    headers = abrir_dev(client)
    criar_consultor_teste(db, "Lab", "lab-ti@horizon.dev", SENHA)
    from app.core.security import hash_senha
    from app.core.tokens import novo_id
    from app.models.base import agora

    agora_ = agora()
    db.add(
        Usuario(
            id=novo_id(),
            nome="Real",
            email="real@horizon.dev",
            senha_hash=hash_senha(SENHA),
            papel="CONSULTOR",
            tipo_conta="NORMAL",
            ativo=True,
            tentativas_falhas=0,
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
    )
    db.commit()

    lista = client.get("/dev/consultores", headers=headers)
    assert lista.status_code == 200
    emails = {item["email"] for item in lista.json()}
    assert "real@horizon.dev" in emails
    assert "lab-ti@horizon.dev" not in emails
