"""Fase 4: mídia em pergunta — MIME real, limites, cópia em modelo (T14)."""

from app.integrations.arquivos import LIMITE_IMAGEM
from app.integrations.cnpj import DadosCnpj
from app.models.pesquisa import Pergunta, TemplatePergunta
from tests.contas import abrir_consultora

# PNG 1x1 mínimo válido
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _rascunho_com_pergunta(client, monkeypatch):
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
            "email_orgao": "rh@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital 1",
        },
    ).json()["id"]
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pid = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Com midia", "tipo": "CLIMA"},
    ).json()["id"]
    pergunta = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Veja a imagem", "tipo": "NOTA_5"},
    ).json()
    return headers, projeto_id, pid, pergunta["id"]


def test_t14_midia_mime_tamanho_e_modelo(client, monkeypatch, db) -> None:
    headers, projeto_id, pid, pergunta_id = _rascunho_com_pergunta(
        client, monkeypatch
    )

    invalido = client.post(
        f"/pesquisas/{pid}/perguntas/{pergunta_id}/midia",
        headers=headers,
        files={"arquivo": ("x.txt", b"nao-e-imagem", "text/plain")},
    )
    assert invalido.status_code == 422

    grande = client.post(
        f"/pesquisas/{pid}/perguntas/{pergunta_id}/midia",
        headers=headers,
        files={
            "arquivo": (
                "grande.png",
                b"\x89PNG\r\n\x1a\n" + b"x" * (LIMITE_IMAGEM + 10),
                "image/png",
            )
        },
    )
    assert grande.status_code == 422

    ok = client.post(
        f"/pesquisas/{pid}/perguntas/{pergunta_id}/midia",
        headers=headers,
        files={"arquivo": ("foto.png", PNG, "image/png")},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["tem_midia"] is True
    assert ok.json()["midia_tipo"] == "IMAGEM"
    assert "foto.png" not in ok.text
    assert "midia_key" not in ok.text

    baixou = client.get(
        f"/pesquisas/{pid}/perguntas/{pergunta_id}/midia",
        headers=headers,
    )
    assert baixou.status_code == 200
    assert baixou.content[:8] == b"\x89PNG\r\n\x1a\n"

    modelo = client.post(
        f"/pesquisas/{pid}/modelo",
        headers=headers,
        json={"nome": "Modelo com midia"},
    )
    assert modelo.status_code == 200
    db.expire_all()
    tpl = (
        db.query(TemplatePergunta)
        .filter(TemplatePergunta.template_id == modelo.json()["id"])
        .one()
    )
    assert tpl.midia_tipo == "IMAGEM"
    assert tpl.midia_key

    copia = client.post(
        f"/projetos/{projeto_id}/pesquisas/de-modelo",
        headers=headers,
        json={"template_id": modelo.json()["id"]},
    )
    assert copia.status_code == 200
    db.expire_all()
    nova = (
        db.query(Pergunta)
        .filter(Pergunta.pesquisa_id == copia.json()["id"])
        .one()
    )
    assert nova.midia_tipo == "IMAGEM"
    assert nova.midia_key
    assert nova.midia_key != tpl.midia_key
