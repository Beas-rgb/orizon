"""P2 restante: GET puro em Minhas pesquisas + resposta por pesquisa_id."""

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import SENHA_FUNC, abrir_consultora


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _token_email(destino: str) -> str:
    return next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == destino
    )


def test_eu_pesquisas_get_nao_grava_token(client, monkeypatch, db):
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = abrir_consultora(client)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto_id = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh-get@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital get",
        },
    ).json()["id"]
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    client.post(
        "/auth/convites",
        headers=headers,
        json={
            "projeto_id": projeto_id,
            "email": "func-get@orgao.dev",
            "papel": "FUNCIONARIO",
            "nome": "Func Get",
        },
    )
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={
            "token": _token_email("func-get@orgao.dev"),
            "senha": SENHA_FUNC,
        },
    )
    func_auth = {"Authorization": f"Bearer {acesso.json()['access_token']}"}
    pid = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "GET puro", "tipo": "CLIMA"},
    ).json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Ok?", "tipo": "NOTA_5"},
    )
    assert client.post(f"/pesquisas/{pid}/publicar", headers=headers).status_code == 200

    from app.models.pesquisa import TokenResposta
    from sqlalchemy import func, select

    antes = db.scalar(select(func.count()).select_from(TokenResposta)) or 0
    lista = client.get("/eu/pesquisas", headers=func_auth)
    assert lista.status_code == 200
    assert lista.json()[0].get("token") in (None, "")
    depois = db.scalar(select(func.count()).select_from(TokenResposta)) or 0
    assert depois == antes

    # Cruzamento: consultora não abre formulário do funcionário
    assert (
        client.get(f"/eu/pesquisas/{pid}/formulario", headers=headers).status_code
        == 404
    )
    form = client.get(f"/eu/pesquisas/{pid}/formulario", headers=func_auth)
    assert form.status_code == 200
