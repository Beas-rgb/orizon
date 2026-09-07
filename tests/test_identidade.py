from sqlalchemy import select

from app.integrations.email import caixa_email
from app.models.auditoria import LogAuditoria
from app.models.usuario import Usuario

SENHA = "senha-segura-1"
OUTRA = "senha-nova-2"


def _token_do_email() -> str:
    corpo = caixa_email.mensagens[-1]["corpo"]
    return corpo.strip().split()[-1]


def test_bootstrap_e_eu(client) -> None:
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "Tia@Horizon.dev", "senha": SENHA},
    )
    assert criado.status_code == 200
    token = criado.json()["access_token"]
    eu = client.get("/auth/eu", headers={"Authorization": f"Bearer {token}"})
    assert eu.status_code == 200
    assert eu.json()["email"] == "tia@horizon.dev"
    assert eu.json()["papel"] == "CONSULTOR"


def test_bootstrap_segunda_vez_bloqueado(client) -> None:
    client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    de_novo = client.post(
        "/auth/bootstrap",
        json={"nome": "Outra", "email": "outra@horizon.dev", "senha": SENHA},
    )
    assert de_novo.status_code == 403


def test_login_senha_errada_nao_revela_e_mail(client) -> None:
    client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    errada = client.post(
        "/auth/login",
        json={"email": "tia@horizon.dev", "senha": "errada-demais"},
    )
    inexistente = client.post(
        "/auth/login",
        json={"email": "ninguem@horizon.dev", "senha": "errada-demais"},
    )
    assert errada.status_code == 401
    assert inexistente.status_code == 401
    assert errada.json()["detail"] == inexistente.json()["detail"]


def test_tres_tentativas_esperam_cinco_minutos(client, db) -> None:
    client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    for _ in range(2):
        resp = client.post(
            "/auth/login",
            json={"email": "tia@horizon.dev", "senha": "errada-demais"},
        )
        assert resp.status_code == 401
    terceira = client.post(
        "/auth/login",
        json={"email": "tia@horizon.dev", "senha": "errada-demais"},
    )
    assert terceira.status_code == 429
    assert "5 minutos" in terceira.json()["detail"]

    certa = client.post(
        "/auth/login",
        json={"email": "tia@horizon.dev", "senha": SENHA},
    )
    assert certa.status_code == 429

    db.expire_all()
    usuario = db.scalar(select(Usuario).where(Usuario.email == "tia@horizon.dev"))
    assert usuario is not None
    assert usuario.bloqueado_ate is not None
    assert usuario.tentativas_falhas >= 3


def test_convite_nao_devolve_token_e_primeiro_acesso(client) -> None:
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    headers = {"Authorization": f"Bearer {criado.json()['access_token']}"}
    convite = client.post(
        "/auth/convites",
        headers=headers,
        json={
            "nome": "Orgão",
            "email": "orgao@cliente.dev",
            "papel": "ORGAO",
        },
    )
    assert convite.status_code == 200
    assert "token" not in convite.json()["mensagem"].lower()
    assert caixa_email.mensagens[-1]["destino"] == "orgao@cliente.dev"
    assert "senha" not in caixa_email.mensagens[-1]["assunto"].lower()

    token = _token_do_email()
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": OUTRA},
    )
    assert acesso.status_code == 200
    eu = client.get(
        "/auth/eu",
        headers={"Authorization": f"Bearer {acesso.json()['access_token']}"},
    )
    assert eu.json()["papel"] == "ORGAO"

    de_novo = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": OUTRA},
    )
    assert de_novo.status_code == 400


def test_orgao_nao_convida(client) -> None:
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    headers = {"Authorization": f"Bearer {criado.json()['access_token']}"}
    client.post(
        "/auth/convites",
        headers=headers,
        json={"nome": "Orgão", "email": "orgao@cliente.dev", "papel": "ORGAO"},
    )
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": _token_do_email(), "senha": OUTRA},
    )
    negado = client.post(
        "/auth/convites",
        headers={"Authorization": f"Bearer {acesso.json()['access_token']}"},
        json={"nome": "Fulano", "email": "f@cliente.dev", "papel": "FUNCIONARIO"},
    )
    assert negado.status_code == 403


def test_recuperacao_no_email_de_acesso(client) -> None:
    client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    pedido = client.post(
        "/auth/recuperar-senha",
        json={"email": "tia@horizon.dev"},
    )
    fantasma = client.post(
        "/auth/recuperar-senha",
        json={"email": "ninguem@horizon.dev"},
    )
    assert pedido.status_code == 200
    assert fantasma.status_code == 200
    assert pedido.json() == fantasma.json()
    assert caixa_email.mensagens[-1]["destino"] == "tia@horizon.dev"
    assert "senha-segura" not in caixa_email.mensagens[-1]["corpo"]

    token = _token_do_email()
    troca = client.post(
        "/auth/redefinir-senha",
        json={"token": token, "senha": OUTRA},
    )
    assert troca.status_code == 200

    antiga = client.post(
        "/auth/login",
        json={"email": "tia@horizon.dev", "senha": SENHA},
    )
    assert antiga.status_code == 401
    nova = client.post(
        "/auth/login",
        json={"email": "tia@horizon.dev", "senha": OUTRA},
    )
    assert nova.status_code == 200

    reuso = client.post(
        "/auth/redefinir-senha",
        json={"token": token, "senha": "terceira-senha"},
    )
    assert reuso.status_code == 400


def test_auditoria_sem_senha(client, db) -> None:
    client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    logs = db.scalars(select(LogAuditoria)).all()
    texto = " ".join(item.acao for item in logs)
    assert "BOOTSTRAP" in texto
    assert SENHA not in texto
