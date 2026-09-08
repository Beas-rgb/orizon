from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import abrir_consultora

SENHA = "Senha-segura1"


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _projeto(client, monkeypatch) -> tuple[dict[str, str], str]:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = abrir_consultora(client)
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
    client.patch(
        f"/projetos/{projeto.json()['id']}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    return headers, projeto.json()["id"]


def test_clima_nao_revela_quem_e_orgao_ve_so_media(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima 2026", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Como está o ambiente?", "tipo": "NOTA_5"},
    )
    client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    token = client.post(
        f"/pesquisas/{pid}/tokens",
        headers=headers,
        params={"quantidade": 1},
    ).json()["tokens"][0]

    pergunta_id = client.get(f"/responder/{token}").json()[0]["id"]
    envio = client.post(
        f"/responder/{token}",
        json={"respostas": [{"pergunta_id": pergunta_id, "valor_numerico": 4}]},
    )
    assert envio.status_code == 200
    assert envio.json()["nota"] is None

    nota = client.get(f"/responder/{token}/nota")
    assert nota.json()["nota"] is None

    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers)
    assert painel.status_code == 200
    assert painel.json()[0]["respostas"] == 1
    assert painel.json()[0]["media"] == 4
    assert "token" not in painel.text


def test_desempenho_devolve_nota_so_com_token(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho", "tipo": "DESEMPENHO"},
    )
    pid = pesquisa.json()["id"]
    pergunta = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Cumpriu a meta?", "tipo": "NOTA_10"},
    )
    client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    token = client.post(f"/pesquisas/{pid}/tokens", headers=headers).json()["tokens"][0]
    convite = next(
        item for item in caixa_email.mensagens if item["destino"] == "rh@prefeitura.dev"
    )
    envio = client.post(
        f"/responder/{token}",
        json={
            "respostas": [
                {"pergunta_id": pergunta.json()["id"], "valor_numerico": 8}
            ]
        },
    )
    assert envio.status_code == 200
    assert envio.json()["nota"] == 8

    token_acesso = convite["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token_acesso, "senha": "Senha-orgao1"},
    )
    orgao = {"Authorization": f"Bearer {acesso.json()['access_token']}"}
    painel = client.get(f"/pesquisas/{pid}/painel", headers=orgao)
    assert painel.status_code == 200
    assert painel.json()[0]["media"] == 8
    assert token not in painel.text


def test_encerra_e_reaproveita_modelo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima 2026", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Como está o ambiente?", "tipo": "NOTA_5"},
    )
    client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    token = client.post(
        f"/pesquisas/{pid}/tokens",
        headers=headers,
        params={"quantidade": 1},
    ).json()["tokens"][0]

    fechada = client.post(f"/pesquisas/{pid}/encerrar", headers=headers)
    assert fechada.status_code == 200
    assert fechada.json()["status"] == "ENCERRADA"
    pergunta_id = "nao-importa"
    negado = client.get(f"/responder/{token}")
    assert negado.status_code == 404

    modelo = client.post(
        f"/pesquisas/{pid}/modelo",
        headers=headers,
        json={"nome": "Clima padrão"},
    )
    assert modelo.status_code == 200
    copia = client.post(
        f"/projetos/{projeto_id}/pesquisas/de-modelo",
        headers=headers,
        json={"template_id": modelo.json()["id"]},
    )
    assert copia.status_code == 200
    assert copia.json()["status"] == "RASCUNHO"
    assert pergunta_id not in copia.text
