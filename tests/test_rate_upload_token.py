"""Upload e geração de token: 3 falhas travam por 5 minutos. Sucesso zera."""

from app.integrations.cnpj import DadosCnpj
from tests.contas import abrir_consultora


def _cnpj(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia="Prefeitura",
        municipio="Brasilia",
        uf="DF",
    )


def _projeto(client, monkeypatch) -> tuple[dict[str, str], str]:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
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
            "vinculo_titulo": "Limite",
        },
    )
    return headers, projeto.json()["id"]


def test_token_de_rascunho_trava_na_quarta(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima", "tipo": "CLIMA"},
    ).json()
    for _ in range(3):
        resp = client.post(f"/pesquisas/{pesquisa['id']}/tokens", headers=headers)
        assert resp.status_code == 422
    quarto = client.post(f"/pesquisas/{pesquisa['id']}/tokens", headers=headers)
    assert quarto.status_code == 429


def test_upload_invalido_trava_e_sucesso_zera(client, monkeypatch) -> None:
    headers, _projeto_id = _projeto(client, monkeypatch)

    def ruim():
        return client.post(
            "/biblioteca",
            headers=headers,
            files={"arquivo": ("x.pdf", b"<html>", "application/pdf")},
        )

    assert ruim().status_code == 422
    assert ruim().status_code == 422
    bom = client.post(
        "/biblioteca",
        headers=headers,
        files={"arquivo": ("nota.txt", b"ola", "text/plain")},
    )
    assert bom.status_code == 200
    assert ruim().status_code == 422
    assert ruim().status_code == 422
    assert ruim().status_code == 422
    assert ruim().status_code == 429
