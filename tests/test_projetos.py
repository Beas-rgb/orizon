from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import abrir_consultora

SENHA = "Senha-segura1"


def _consultora(client) -> dict[str, str]:
    return abrir_consultora(client)


def _cnpj_falso(cnpj: str) -> DadosCnpj:
    digitos = "".join(ch for ch in cnpj if ch.isdigit())
    if digitos == "00000000000191":
        return DadosCnpj(
            cnpj="00000000000191",
            razao_social="Camara Exemplo",
            nome_fantasia="Camara",
            municipio="Goiania",
            uf="GO",
        )
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia="Prefeitura",
        municipio="Brasilia",
        uf="DF",
    )


def _criar_projeto(client, headers, rotulo_id, cnpj, email, titulo):
    return client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": rotulo_id,
            "cnpj": cnpj,
            "email_orgao": email,
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": titulo,
        },
    )


def test_rotulos_vem_do_banco(client) -> None:
    headers = _consultora(client)
    resp = client.get("/projetos/rotulos", headers=headers)
    assert resp.status_code == 200
    nomes = {item["nome"] for item in resp.json()}
    assert "Clima organizacional" in nomes
    assert "Desempenho" in nomes


def test_cria_projeto_puxa_cnpj_e_envia_email(client, monkeypatch) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = _consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")

    criado = _criar_projeto(
        client,
        headers,
        clima["id"],
        "19.131.243/0001-97",
        "rh@prefeitura.dev",
        "Edital 12/2026",
    )
    assert criado.status_code == 200
    corpo = criado.json()
    assert corpo["razao_social"] == "Prefeitura Exemplo"
    assert corpo["rotulo"] == "Clima organizacional"
    assert corpo["vinculo_tipo"] == "EDITAL"
    assert corpo["email_orgao"] == "rh@prefeitura.dev"
    assert corpo["convite_entrega"] == "ENVIADO"
    assert caixa_email.mensagens[-1]["destino"] == "rh@prefeitura.dev"
    assert SENHA not in caixa_email.mensagens[-1]["corpo"]

    lista = client.get("/projetos", headers=headers)
    assert lista.status_code == 200
    assert len(lista.json()) == 1
    assert lista.json()[0]["id"] == corpo["id"]


def test_segundo_cliente_recebe_convite_do_orgao(client, monkeypatch) -> None:
    """B1: órgão é por projeto. O segundo CNPJ não pode ficar sem convite."""
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = _consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")

    primeiro = _criar_projeto(
        client,
        headers,
        clima["id"],
        "19131243000197",
        "rh@prefeitura.dev",
        "Edital A",
    )
    assert primeiro.status_code == 200
    assert primeiro.json()["convite_entrega"] == "ENVIADO"
    assert caixa_email.mensagens[-1]["destino"] == "rh@prefeitura.dev"

    segundo = _criar_projeto(
        client,
        headers,
        clima["id"],
        "00000000000191",
        "rh@camara.dev",
        "Edital B",
    )
    assert segundo.status_code == 200
    assert segundo.json()["convite_entrega"] == "ENVIADO"
    assert segundo.json()["email_orgao"] == "rh@camara.dev"
    assert caixa_email.mensagens[-1]["destino"] == "rh@camara.dev"
    assert primeiro.json()["id"] != segundo.json()["id"]


def test_orgao_do_projeto_1_nao_abre_projeto_2(client, monkeypatch) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = _consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")

    a = _criar_projeto(
        client,
        headers,
        clima["id"],
        "19131243000197",
        "rh@prefeitura.dev",
        "Edital A",
    )
    b = _criar_projeto(
        client,
        headers,
        clima["id"],
        "00000000000191",
        "rh@camara.dev",
        "Edital B",
    )
    projeto_a = a.json()["id"]
    projeto_b = b.json()["id"]

    token_a = next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == "rh@prefeitura.dev"
    )
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token_a, "senha": "Senha-orgao1"},
    )
    orgao_a = {"Authorization": f"Bearer {acesso.json()['access_token']}"}

    lista = client.get("/projetos", headers=orgao_a)
    assert [item["id"] for item in lista.json()] == [projeto_a]
    alheio = client.get(f"/projetos/{projeto_b}", headers=orgao_a)
    assert alheio.status_code == 404
    config = client.get(f"/projetos/{projeto_b}/configuracao", headers=orgao_a)
    assert config.status_code == 404


def test_convite_cancelado_do_projeto_1_nao_bloqueia_projeto_2(
    client, monkeypatch
) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = _consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")

    a = _criar_projeto(
        client,
        headers,
        clima["id"],
        "19131243000197",
        "rh@prefeitura.dev",
        "Edital A",
    )
    projeto_a = a.json()["id"]
    reenvio = client.post(
        f"/projetos/{projeto_a}/reenviar-convite",
        headers=headers,
    )
    assert reenvio.status_code == 200

    b = _criar_projeto(
        client,
        headers,
        clima["id"],
        "00000000000191",
        "rh@camara.dev",
        "Edital B",
    )
    assert b.status_code == 200
    assert b.json()["convite_entrega"] == "ENVIADO"
    assert caixa_email.mensagens[-1]["destino"] == "rh@camara.dev"


def test_orgao_so_ve_o_proprio_projeto(client, monkeypatch) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = _consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    criado = _criar_projeto(
        client,
        headers,
        clima["id"],
        "19131243000197",
        "rh@prefeitura.dev",
        "Termo de referência",
    )
    projeto_id = criado.json()["id"]
    token = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": "Senha-orgao1"},
    )
    orgao = {"Authorization": f"Bearer {acesso.json()['access_token']}"}

    lista = client.get("/projetos", headers=orgao)
    assert lista.status_code == 200
    assert [item["id"] for item in lista.json()] == [projeto_id]

    outro = client.post(
        "/auth/bootstrap",
        json={"nome": "Outra", "email": "outra@horizon.dev", "senha": SENHA},
    )
    assert outro.status_code == 403

    alheio = client.get(
        "/projetos/00000000-0000-0000-0000-000000000099",
        headers=orgao,
    )
    assert alheio.status_code == 404

    equipe = client.get(f"/projetos/{projeto_id}/equipe", headers=headers)
    assert equipe.status_code == 200
    assert equipe.json()[0]["email"] == "rh@prefeitura.dev"
    assert equipe.json()[0]["papel"] == "ORGAO"
    assert equipe.json()[0]["situacao"] == "ATIVO"
    assert "token" not in equipe.text

    negado = client.get(f"/projetos/{projeto_id}/equipe", headers=orgao)
    assert negado.status_code == 404
