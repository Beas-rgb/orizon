"""Regressão das falhas encontradas na auditoria de 18/09.

Duas coisas são cobertas aqui:
1. A rota do SPA não pode servir arquivo de fora de `web/app`.
2. A biblioteca não pode aceitar arquivo cujo conteúdo desmente o
   Content-Type declarado pelo navegador.
"""

from app.integrations.cnpj import DadosCnpj
from tests.contas import abrir_consultora

PDF = b"%PDF-1.4 teste"
HTML = b"<html><script>alert(1)</script></html>"

# `..%2f` e `%2e%2e%2f` chegam decodificados no parametro de caminho; foi por
# aqui que `/app/..%2f..%2f.env` devolveu os segredos do servidor.
FUGAS = (
    "/app/..%2f..%2f.env",
    "/app/%2e%2e%2f%2e%2e%2f.env",
    "/app/..%2f..%2fpyproject.toml",
    "/app/..%2f..%2fdata%2foutbox%2fultimo.txt",
    "/app/..%2f..%2f..%2f.env",
    "/app/../../.env",
)


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def test_spa_nao_serve_arquivo_fora_do_build(client) -> None:
    for caminho in FUGAS:
        resposta = client.get(caminho)
        assert resposta.status_code == 404, caminho
        assert b"JWT_SECRET" not in resposta.content, caminho
        assert b"DATABASE_URL" not in resposta.content, caminho


def test_spa_continua_servindo_a_tela(client) -> None:
    resposta = client.get("/app/login")
    assert resposta.status_code == 200
    assert b"<div id=\"root\"" in resposta.content


def _consultora_com_projeto(client, monkeypatch) -> tuple[dict[str, str], str]:
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
    return headers, projeto.json()["id"]


def test_biblioteca_recusa_html_disfarcado_de_pdf(client, monkeypatch) -> None:
    headers, projeto_id = _consultora_com_projeto(client, monkeypatch)
    resposta = client.post(
        "/biblioteca",
        headers=headers,
        data={"projeto_id": projeto_id, "camada": "EXTERNA"},
        files={"arquivo": ("edital.pdf", HTML, "application/pdf")},
    )
    assert resposta.status_code == 422
    assert "não corresponde" in resposta.json()["detail"]


def test_biblioteca_recusa_texto_com_html(client, monkeypatch) -> None:
    headers, projeto_id = _consultora_com_projeto(client, monkeypatch)
    resposta = client.post(
        "/biblioteca",
        headers=headers,
        data={"projeto_id": projeto_id, "camada": "EXTERNA"},
        files={"arquivo": ("nota.txt", HTML, "text/plain")},
    )
    assert resposta.status_code == 422


def test_biblioteca_aceita_pdf_de_verdade(client, monkeypatch) -> None:
    headers, projeto_id = _consultora_com_projeto(client, monkeypatch)
    resposta = client.post(
        "/biblioteca",
        headers=headers,
        data={"projeto_id": projeto_id, "camada": "EXTERNA"},
        files={"arquivo": ("edital.pdf", PDF, "application/pdf")},
    )
    assert resposta.status_code == 200
    baixou = client.get(
        f"/biblioteca/{resposta.json()['id']}/arquivo",
        headers=headers,
    )
    assert baixou.content == PDF
    assert baixou.headers["x-content-type-options"] == "nosniff"


def test_biblioteca_aceita_texto_puro(client, monkeypatch) -> None:
    headers, projeto_id = _consultora_com_projeto(client, monkeypatch)
    resposta = client.post(
        "/biblioteca",
        headers=headers,
        data={"projeto_id": projeto_id, "camada": "EXTERNA"},
        files={"arquivo": ("nota.txt", b"anotacao do projeto", "text/plain")},
    )
    assert resposta.status_code == 200
