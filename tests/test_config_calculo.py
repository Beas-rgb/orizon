"""Configuração de cálculo da pesquisa: JSON estruturado, sem código."""

from app.integrations.cnpj import DadosCnpj
from tests.contas import abrir_consultora


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia="Prefeitura",
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
            "vinculo_titulo": "Config",
        },
    )
    return headers, projeto.json()["id"]


def test_config_calculo_aceita_json_estruturado(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho 2026", "tipo": "DESEMPENHO"},
    ).json()
    resp = client.patch(
        f"/pesquisas/{pesquisa['id']}",
        headers=headers,
        json={
            "config_calculo": (
                '{"pesos": {"auto": 1, "superior": 2}, '
                '"escala": {"min": 1, "max": 5}}'
            )
        },
    )
    assert resp.status_code == 200


def test_config_calculo_rejeita_codigo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho 2026", "tipo": "DESEMPENHO"},
    ).json()
    resp = client.patch(
        f"/pesquisas/{pesquisa['id']}",
        headers=headers,
        json={"config_calculo": '{"eval": "1+1"}'},
    )
    assert resp.status_code == 422
    assert "código" in resp.json()["detail"].lower()


def test_config_calculo_rejeita_json_invalido(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho 2026", "tipo": "DESEMPENHO"},
    ).json()
    resp = client.patch(
        f"/pesquisas/{pesquisa['id']}",
        headers=headers,
        json={"config_calculo": "nao-e-json"},
    )
    assert resp.status_code == 422


def test_config_calculo_rejeita_peso_negativo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Desempenho 2026", "tipo": "DESEMPENHO"},
    ).json()
    resp = client.patch(
        f"/pesquisas/{pesquisa['id']}",
        headers=headers,
        json={"config_calculo": '{"pesos": {"auto": -1}}'},
    )
    assert resp.status_code == 422
