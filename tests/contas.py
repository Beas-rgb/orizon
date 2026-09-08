"""Contas dos testes. A primeira é o dev. A consultora só nasce se ele autorizar."""

from app.integrations.email import caixa_email

SENHA = "Senha-segura1"
SENHA_ORGAO = "Senha-orgao1"
SENHA_FUNC = "Senha-func1!"


def abrir_dev(client, email: str = "joao@horizon.dev") -> dict[str, str]:
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Joao", "email": email, "senha": SENHA},
    )
    if criado.status_code != 200:
        criado = client.post(
            "/auth/login",
            json={"email": email, "senha": SENHA},
        )
    return {"Authorization": f"Bearer {criado.json()['access_token']}"}


def abrir_consultora(
    client,
    email: str = "tia@horizon.dev",
    nome: str = "Tia",
) -> dict[str, str]:
    dev = abrir_dev(client)
    pedido = client.post(
        "/auth/cadastro-consultora",
        json={"nome": nome, "email": email},
    )
    assert pedido.status_code == 200
    lista = client.get("/dev/pedidos", headers=dev)
    assert lista.status_code == 200
    autorizado = client.post(
        f"/dev/pedidos/{lista.json()[0]['id']}/autorizar",
        headers=dev,
    )
    assert autorizado.status_code == 200
    token = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": SENHA},
    )
    assert acesso.status_code == 200
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}
