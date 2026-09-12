"""Reenvio de convite de funcionário pendente."""

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import SENHA, abrir_consultora


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Orgao Teste",
        nome_fantasia="Orgao",
        municipio="Brasilia",
        uf="DF",
    )


def test_reenviar_convite_funcionario_invalida_token_antigo(
    client, monkeypatch
) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = abrir_consultora(client, "reenv-func@hz.dev", "Reenv Func")
    rotulo = client.get("/projetos/rotulos", headers=headers).json()[0]["id"]
    projeto = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": rotulo,
            "cnpj": "19131243000197",
            "email_orgao": "orgao-reenv@hz.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital reenvio",
        },
    )
    assert projeto.status_code == 200
    pid = projeto.json()["id"]

    convite = client.post(
        "/auth/convites",
        headers=headers,
        json={
            "nome": "Func Um",
            "email": "func-reenv@hz.dev",
            "papel": "FUNCIONARIO",
            "projeto_id": pid,
        },
    )
    assert convite.status_code == 200
    token_antigo = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]

    reenvio = client.post(
        f"/projetos/{pid}/reenviar-convite-funcionario",
        headers=headers,
        json={"email": "func-reenv@hz.dev"},
    )
    assert reenvio.status_code == 200
    assert reenvio.json()["email"] == "func-reenv@hz.dev"
    token_novo = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    assert token_novo != token_antigo

    falha = client.post(
        "/auth/primeiro-acesso",
        json={"token": token_antigo, "senha": SENHA},
    )
    assert falha.status_code == 400

    ok = client.post(
        "/auth/primeiro-acesso",
        json={"token": token_novo, "senha": SENHA},
    )
    assert ok.status_code == 200
    assert ok.json()["painel"] == "funcionario"

    equipe = client.get(f"/projetos/{pid}/equipe", headers=headers)
    assert equipe.status_code == 200
    emails = {m["email"] for m in equipe.json()}
    assert "func-reenv@hz.dev" in emails
