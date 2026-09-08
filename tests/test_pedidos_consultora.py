from app.integrations.email import caixa_email
from tests.contas import SENHA, abrir_consultora, abrir_dev


def test_consultora_so_entra_depois_da_autorizacao(client) -> None:
    dev = abrir_dev(client)
    pedido = client.post(
        "/auth/cadastro-consultora",
        json={"nome": "Tia", "email": "tia@horizon.dev"},
    )
    assert pedido.status_code == 200
    assert "token" not in pedido.text.lower()

    cedo = client.post(
        "/auth/login",
        json={"email": "tia@horizon.dev", "senha": SENHA},
    )
    assert cedo.status_code == 401

    lista = client.get("/dev/pedidos", headers=dev)
    assert lista.status_code == 200
    assert lista.json()[0]["email"] == "tia@horizon.dev"

    negado = client.get("/dev/pedidos")
    assert negado.status_code == 401

    autorizado = client.post(
        f"/dev/pedidos/{lista.json()[0]['id']}/autorizar",
        headers=dev,
    )
    assert autorizado.status_code == 200
    assert "senha" not in caixa_email.mensagens[-1]["assunto"].lower()

    token = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": "fraca"},
    )
    assert acesso.status_code == 422

    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": SENHA},
    )
    assert acesso.status_code == 200
    assert acesso.json()["painel"] == "consultora"
    assert acesso.json()["access_token"]
    assert "senha" not in acesso.text.lower() or "senha_hash" not in acesso.text

    cadastradas = client.get("/dev/consultores", headers=dev)
    assert cadastradas.json()[0]["email"] == "tia@horizon.dev"
    assert cadastradas.json()[0]["ativo"] is True

    outra = abrir_consultora(client, email="outra@horizon.dev", nome="Outra")
    assert outra["Authorization"].startswith("Bearer ")


def test_diagnostico_so_para_o_dev(client) -> None:
    consultora = abrir_consultora(client)
    negado = client.get("/dev/diagnostico", headers=consultora)
    assert negado.status_code == 404

    dev = abrir_dev(client)
    analise = client.get("/dev/diagnostico", headers=dev)
    assert analise.status_code == 200
    corpo = analise.json()
    assert corpo["api"] == "ok"
    assert corpo["banco"] == "ok"
    assert "DATABASE_URL" not in analise.text
    assert corpo["contas"]["CONSULTOR"] == 1
