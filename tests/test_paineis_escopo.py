"""Auditoria de escopo: órgão e funcionário não cruzam projeto (IDOR → 404)."""

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import SENHA_FUNC, SENHA_ORGAO, abrir_consultora


def _cnpj(cnpj: str) -> DadosCnpj:
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


def _dois_projetos(client, monkeypatch):
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    a = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Projeto A",
        },
    ).json()
    b = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "00000000000191",
            "email_orgao": "rh@camara.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Projeto B",
        },
    ).json()
    return headers, a["id"], b["id"]


def _token_email(destino: str) -> str:
    return next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == destino
    )


def _entrar(client, destino: str, senha: str) -> dict[str, str]:
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": _token_email(destino), "senha": senha},
    )
    assert acesso.status_code == 200
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}


def test_orgao_nao_cria_edita_nem_lista_equipe_alheia(client, monkeypatch) -> None:
    headers, projeto_a, projeto_b = _dois_projetos(client, monkeypatch)
    orgao = _entrar(client, "rh@prefeitura.dev", SENHA_ORGAO)

    assert [item["id"] for item in client.get("/projetos", headers=orgao).json()] == [
        projeto_a
    ]
    assert client.get(f"/projetos/{projeto_b}", headers=orgao).status_code == 404
    assert (
        client.post(
            "/projetos",
            headers=orgao,
            json={
                "rotulo_id": "x",
                "cnpj": "19131243000197",
                "email_orgao": "outro@x.dev",
                "vinculo_tipo": "EDITAL",
                "vinculo_titulo": "Hack",
            },
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/projetos/{projeto_a}",
            headers=orgao,
            json={"estado": "ENCERRADO"},
        ).status_code
        == 404
    )
    assert client.get(f"/projetos/{projeto_a}/equipe", headers=orgao).status_code == 404
    assert client.get(f"/projetos/{projeto_b}/equipe", headers=orgao).status_code == 404
    assert (
        client.patch(
            f"/projetos/{projeto_a}/configuracao",
            headers=orgao,
            json={"pesquisas_habilitadas": True},
        ).status_code
        == 404
    )
    convite_orgao = client.post(
        "/auth/convites",
        headers=orgao,
        json={
            "nome": "Outro",
            "email": "x@y.dev",
            "papel": "FUNCIONARIO",
            "projeto_id": projeto_a,
        },
    )
    assert convite_orgao.status_code == 403
    assert "consultora" in convite_orgao.json()["detail"].lower()
    # Consultora ainda opera o próprio projeto.
    equipe = client.get(f"/projetos/{projeto_a}/equipe", headers=headers)
    assert equipe.status_code == 200


def test_funcionario_so_ve_o_proprio_projeto_e_nao_muta(client, monkeypatch) -> None:
    headers, projeto_a, projeto_b = _dois_projetos(client, monkeypatch)
    convite = client.post(
        "/auth/convites",
        headers=headers,
        json={
            "nome": "Servidor",
            "email": "servidor@prefeitura.dev",
            "papel": "FUNCIONARIO",
            "projeto_id": projeto_a,
        },
    )
    assert convite.status_code == 200
    func = _entrar(client, "servidor@prefeitura.dev", SENHA_FUNC)

    lista = client.get("/projetos", headers=func)
    assert lista.status_code == 200
    assert [item["id"] for item in lista.json()] == [projeto_a]
    assert client.get(f"/projetos/{projeto_b}", headers=func).status_code == 404
    assert client.get(f"/projetos/{projeto_a}/equipe", headers=func).status_code == 404
    assert (
        client.post(
            f"/projetos/{projeto_a}/pesquisas",
            headers=func,
            json={"titulo": "Hack", "tipo": "CLIMA"},
        ).status_code
        == 404
    )
    assert (
        client.get(f"/projetos/{projeto_a}/pesquisas", headers=func).status_code == 404
    )
    assert (
        client.patch(
            f"/projetos/{projeto_a}/configuracao",
            headers=func,
            json={"pesquisas_habilitadas": True},
        ).status_code
        == 404
    )
    assert client.get("/auth/eu", headers=func).json()["painel"] == "funcionario"
