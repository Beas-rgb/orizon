"""Fase 5: Minhas pesquisas (6.8) e participantes (status)."""

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


def _entrar(client, destino: str, senha: str) -> dict[str, str]:
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": _token_email(destino), "senha": senha},
    )
    assert acesso.status_code == 200
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}


def test_minhas_pesquisas_e_participantes(client, monkeypatch):
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
            "email_orgao": "rh68@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital 68",
        },
    )
    projeto_id = projeto.json()["id"]
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
            "email": "func68@orgao.dev",
            "papel": "FUNCIONARIO",
            "nome": "Func 68",
        },
    )
    func = _entrar(client, "func68@orgao.dev", SENHA_FUNC)

    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima 68", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Como está?", "tipo": "NOTA_5"},
    )
    assert client.post(f"/pesquisas/{pid}/publicar", headers=headers).status_code == 200

    minhas = client.get("/eu/pesquisas", headers=func)
    assert minhas.status_code == 200
    itens = minhas.json()
    assert len(itens) == 1
    assert itens[0]["titulo"] == "Clima 68"
    assert itens[0]["status_participacao"] == "PENDENTE"
    assert itens[0].get("token") in (None, "")
    assert itens[0]["pesquisa_id"] == pid

    form = client.get(f"/eu/pesquisas/{pid}/formulario", headers=func)
    assert form.status_code == 200
    assert form.json()[0]["texto"] == "Como está?"

    parts = client.get(f"/pesquisas/{pid}/participantes", headers=headers)
    assert parts.status_code == 200
    corpo = parts.json()
    assert corpo["agregado"] is True
    assert corpo["total"] == 1
    assert corpo["respondidas"] == 0
    assert corpo["itens"] is None
    assert "email" not in str(corpo).lower() or "func68" not in str(corpo)

    # Funcionário não vê participantes
    assert client.get(f"/pesquisas/{pid}/participantes", headers=func).status_code == 404

    # Consultora não tem minhas pesquisas
    assert client.get("/eu/pesquisas", headers=headers).json() == []
