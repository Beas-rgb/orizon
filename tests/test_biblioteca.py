from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email

SENHA = "senha-segura-1"
PDF = b"%PDF-1.4 teste"


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _consultora_e_projeto(client, monkeypatch) -> tuple[dict[str, str], str]:
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


def _orgao(client) -> dict[str, str]:
    token = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": "senha-orgao-1"},
    )
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}


def test_padrao_e_privado_so_para_a_consultora(client, monkeypatch) -> None:
    headers, projeto_id = _consultora_e_projeto(client, monkeypatch)
    enviado = client.post(
        "/biblioteca",
        headers=headers,
        files={"arquivo": ("edital.pdf", PDF, "application/pdf")},
        data={"projeto_id": projeto_id},
    )
    assert enviado.status_code == 200
    corpo = enviado.json()
    assert corpo["visibilidade"] == "PRIVADO"
    assert corpo["camada"] == "EXTERNA"

    orgao = _orgao(client)
    lista = client.get("/biblioteca", headers=orgao, params={"projeto_id": projeto_id})
    assert lista.status_code == 200
    assert lista.json() == []
    direto = client.get(f"/biblioteca/{corpo['id']}/arquivo", headers=orgao)
    assert direto.status_code == 404


def test_interna_so_abre_depois_que_a_consultora_escolhe(client, monkeypatch) -> None:
    headers, projeto_id = _consultora_e_projeto(client, monkeypatch)
    enviado = client.post(
        "/biblioteca",
        headers=headers,
        files={"arquivo": ("nota.pdf", PDF, "application/pdf")},
        data={"projeto_id": projeto_id, "camada": "INTERNA"},
    )
    assert enviado.json()["visibilidade"] == "PRIVADO"
    doc_id = enviado.json()["id"]
    orgao = _orgao(client)
    assert client.get(f"/biblioteca/{doc_id}", headers=orgao).status_code == 404

    aberto = client.patch(
        f"/biblioteca/{doc_id}",
        headers=headers,
        json={"visibilidade": "ORGAO"},
    )
    assert aberto.status_code == 200
    assert aberto.json()["visibilidade"] == "ORGAO"
    baixou = client.get(f"/biblioteca/{doc_id}/arquivo", headers=orgao)
    assert baixou.status_code == 200
    assert baixou.content == PDF


def test_externa_nao_abre_para_o_orgao_mesmo_se_pedirem(client, monkeypatch) -> None:
    headers, projeto_id = _consultora_e_projeto(client, monkeypatch)
    enviado = client.post(
        "/biblioteca",
        headers=headers,
        files={"arquivo": ("rascunho.pdf", PDF, "application/pdf")},
        data={
            "projeto_id": projeto_id,
            "camada": "EXTERNA",
            "visibilidade": "PUBLICO_PROJETO",
        },
    )
    assert enviado.json()["visibilidade"] == "PRIVADO"
    orgao = _orgao(client)
    troca = client.patch(
        f"/biblioteca/{enviado.json()['id']}",
        headers=orgao,
        json={"visibilidade": "ORGAO"},
    )
    assert troca.status_code == 404
