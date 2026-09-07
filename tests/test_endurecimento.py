import logging

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email

SENHA = "senha-segura-1"


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _consultora(client, monkeypatch) -> tuple[dict[str, str], str]:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    headers = {"Authorization": f"Bearer {criado.json()['access_token']}"}
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital 1",
        },
    )
    return headers, projeto.json()["id"]


def test_login_de_email_abre_o_painel_do_papel(client, monkeypatch) -> None:
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    headers = {"Authorization": f"Bearer {criado.json()['access_token']}"}
    dev = client.post(
        "/auth/convites",
        headers=headers,
        json={"nome": "Dev", "email": "dev@horizon.dev", "papel": "TI"},
    )
    assert dev.status_code == 200
    outro = client.post(
        "/auth/convites",
        headers=headers,
        json={"nome": "Outro", "email": "outro-dev@horizon.dev", "papel": "TI"},
    )
    assert outro.status_code == 409
    assert criado.json()["painel"] == "consultora"
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital 1",
        },
    )
    funcionario = client.post(
        "/auth/convites",
        headers=headers,
        json={
            "nome": "Servidor",
            "email": "servidor@prefeitura.dev",
            "papel": "FUNCIONARIO",
            "projeto_id": projeto.json()["id"],
        },
    )
    assert funcionario.status_code == 200
    convite = next(
        item
        for item in caixa_email.mensagens
        if item["destino"] == "servidor@prefeitura.dev"
    )
    token = convite["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": "senha-func-1"},
    )
    assert acesso.json()["painel"] == "funcionario"
    entrada = client.post(
        "/auth/login",
        json={"email": "servidor@prefeitura.dev", "senha": "senha-func-1"},
    )
    assert entrada.status_code == 200
    assert entrada.json()["painel"] == "funcionario"
    eu = client.get(
        "/auth/eu",
        headers={"Authorization": f"Bearer {entrada.json()['access_token']}"},
    )
    assert eu.json()["painel"] == "funcionario"


def test_orgao_nao_abre_pesquisa_de_outro_projeto(client, monkeypatch) -> None:
    headers, projeto_id = _consultora(client, monkeypatch)
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    token = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": "senha-orgao-1"},
    )
    orgao = {"Authorization": f"Bearer {acesso.json()['access_token']}"}

    alheio = client.get(
        "/projetos/00000000-0000-0000-0000-000000000099/pesquisas",
        headers=orgao,
    )
    assert alheio.status_code == 404
    painel = client.get(f"/pesquisas/{pid}/painel", headers=orgao)
    assert painel.status_code == 200
    pergunta = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=orgao,
        json={"texto": "Não pode", "tipo": "TEXTO_LIVRE"},
    )
    assert pergunta.status_code == 404


def test_log_nao_grava_token_do_link(client, monkeypatch, caplog) -> None:
    headers, projeto_id = _consultora(client, monkeypatch)
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Como está?", "tipo": "NOTA_5"},
    )
    client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    token = client.post(
        f"/pesquisas/{pid}/tokens",
        headers=headers,
        params={"quantidade": 1},
    ).json()["tokens"][0]
    with caplog.at_level(logging.INFO, logger="horizon.acesso"):
        client.get(f"/responder/{token}")
    texto = "\n".join(caplog.messages)
    assert token not in texto
    assert "/responder/[token]" in texto
