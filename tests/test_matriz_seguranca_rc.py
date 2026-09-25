"""Matriz A→B do Release Candidate: árvore, importação e ciclo.

Consultora B, órgão A e funcionário A não leem nem gravam o projeto alheio.
Falha → 404 (não confirma existência).
"""

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


def _token_email(destino: str) -> str:
    return next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == destino
    )


def _cenario(client, monkeypatch):
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    a = abrir_consultora(client, email="tia-a@horizon.dev", nome="Tia A")
    b = abrir_consultora(client, email="tia-b@horizon.dev", nome="Tia B")
    rotulos = client.get("/projetos/rotulos", headers=a).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto_a = client.post(
        "/projetos",
        headers=a,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh-a@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Projeto A",
        },
    ).json()["id"]
    projeto_b = client.post(
        "/projetos",
        headers=b,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "00000000000191",
            "email_orgao": "rh-b@camara.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Projeto B",
        },
    ).json()["id"]
    client.post(
        "/auth/convites",
        headers=a,
        json={
            "projeto_id": projeto_a,
            "email": "func-a@prefeitura.dev",
            "papel": "FUNCIONARIO",
            "nome": "Func A",
        },
    )
    orgao_a = {
        "Authorization": (
            "Bearer "
            + client.post(
                "/auth/primeiro-acesso",
                json={
                    "token": _token_email("rh-a@prefeitura.dev"),
                    "senha": SENHA_ORGAO,
                },
            ).json()["access_token"]
        )
    }
    func_a = {
        "Authorization": (
            "Bearer "
            + client.post(
                "/auth/primeiro-acesso",
                json={
                    "token": _token_email("func-a@prefeitura.dev"),
                    "senha": SENHA_FUNC,
                },
            ).json()["access_token"]
        )
    }
    ciclo_b = client.post(
        f"/projetos/{projeto_b}/ciclos",
        headers=b,
        json={"nome": "Ciclo B"},
    ).json()["id"]
    return a, b, projeto_a, projeto_b, orgao_a, func_a, ciclo_b


def test_consultora_b_nao_le_nem_grava_projeto_a(client, monkeypatch) -> None:
    _a, b, projeto_a, _pb, _oa, _fa, _cb = _cenario(client, monkeypatch)
    csv = (
        b"nome;email;cargo;setor;superior_email\n"
        b"Ana;ana@x.dev;Analista;RH;\n"
    )
    assert client.get(f"/projetos/{projeto_a}/arvore", headers=b).status_code == 404
    assert (
        client.post(
            f"/projetos/{projeto_a}/importar/previa",
            headers=b,
            files={"arquivo": ("eq.csv", csv, "text/csv")},
        ).status_code
        == 404
    )
    assert client.get(f"/projetos/{projeto_a}/ciclos", headers=b).status_code == 404
    assert (
        client.post(
            f"/projetos/{projeto_a}/ciclos",
            headers=b,
            json={"nome": "Hack"},
        ).status_code
        == 404
    )


def test_orgao_e_funcionario_nao_cruzam_ciclo_nem_arvore(client, monkeypatch) -> None:
    _a, _b, projeto_a, projeto_b, orgao_a, func_a, ciclo_b = _cenario(
        client, monkeypatch
    )
    arvore_b = client.get(f"/projetos/{projeto_b}/arvore", headers=orgao_a)
    assert arvore_b.status_code == 404
    ciclos_b = client.get(f"/projetos/{projeto_b}/ciclos", headers=orgao_a)
    assert ciclos_b.status_code == 404
    relacoes_b = client.get(f"/ciclos/{ciclo_b}/relacoes", headers=orgao_a)
    assert relacoes_b.status_code == 404
    arvore_func_b = client.get(f"/projetos/{projeto_b}/arvore", headers=func_a)
    assert arvore_func_b.status_code == 404
    arvore_func_a = client.get(f"/projetos/{projeto_a}/arvore", headers=func_a)
    assert arvore_func_a.status_code == 404
    assert (
        client.post(
            f"/ciclos/{ciclo_b}/gerar-relacoes",
            headers=func_a,
        ).status_code
        == 404
    )
    arvore_propria = client.get(f"/projetos/{projeto_a}/arvore", headers=orgao_a)
    assert arvore_propria.status_code == 200
