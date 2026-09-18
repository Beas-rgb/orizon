"""Fase 3: editar/excluir/reordenar perguntas só em RASCUNHO (T11–T13)."""

from app.integrations.cnpj import DadosCnpj
from tests.contas import abrir_consultora


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _rascunho(client, monkeypatch):
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
        json={"titulo": "Rascunho", "tipo": "CLIMA", "descricao": "v1"},
    ).json()["id"]
    return headers, pid


def test_t11_editar_rascunho_ok_publicada_422(client, monkeypatch) -> None:
    headers, pid = _rascunho(client, monkeypatch)
    p1 = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Pergunta A", "tipo": "NOTA_5"},
    ).json()

    editada = client.patch(
        f"/pesquisas/{pid}/perguntas/{p1['id']}",
        headers=headers,
        json={"texto": "Pergunta A editada"},
    )
    assert editada.status_code == 200
    assert editada.json()["texto"] == "Pergunta A editada"

    meta = client.patch(
        f"/pesquisas/{pid}",
        headers=headers,
        json={"titulo": "Novo título", "descricao": "v2"},
    )
    assert meta.status_code == 200
    assert meta.json()["titulo"] == "Novo título"
    assert meta.json()["descricao"] == "v2"

    client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    negada = client.patch(
        f"/pesquisas/{pid}/perguntas/{p1['id']}",
        headers=headers,
        json={"texto": "Não pode"},
    )
    assert negada.status_code == 422
    assert "publicada" in negada.json()["detail"].lower()

    negada_meta = client.patch(
        f"/pesquisas/{pid}",
        headers=headers,
        json={"titulo": "Também não"},
    )
    assert negada_meta.status_code == 422


def test_t12_excluir_reordena_sem_colisao(client, monkeypatch) -> None:
    headers, pid = _rascunho(client, monkeypatch)
    ids = []
    for texto in ("Uma", "Duas", "Três"):
        criada = client.post(
            f"/pesquisas/{pid}/perguntas",
            headers=headers,
            json={"texto": texto, "tipo": "NOTA_5"},
        ).json()
        ids.append(criada["id"])
        assert criada["ordem"] == len(ids)

    removida = client.delete(
        f"/pesquisas/{pid}/perguntas/{ids[1]}",
        headers=headers,
    )
    assert removida.status_code == 200

    # Soft-delete no meio: as restantes ficam com ordem 1 e 2, sem colisão.
    restantes = client.post(
        f"/pesquisas/{pid}/perguntas/reordenar",
        headers=headers,
        json={"pergunta_ids": [ids[0], ids[2]]},
    )
    assert restantes.status_code == 200
    corpo = restantes.json()
    assert len(corpo) == 2
    assert [item["ordem"] for item in corpo] == [1, 2]
    assert {item["id"] for item in corpo} == {ids[0], ids[2]}


def test_t13_reordenar_persiste(client, monkeypatch) -> None:
    headers, pid = _rascunho(client, monkeypatch)
    cria_a = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Alpha", "tipo": "NOTA_5"},
    )
    cria_b = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Beta", "tipo": "NOTA_5"},
    )
    cria_c = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Gama", "tipo": "NOTA_5"},
    )
    assert cria_a.status_code == 200, cria_a.text
    assert cria_b.status_code == 200, cria_b.text
    assert cria_c.status_code == 200, cria_c.text
    pergunta_a = cria_a.json()
    pergunta_b = cria_b.json()
    pergunta_c = cria_c.json()

    nova = client.post(
        f"/pesquisas/{pid}/perguntas/reordenar",
        headers=headers,
        json={
            "pergunta_ids": [
                pergunta_c["id"],
                pergunta_a["id"],
                pergunta_b["id"],
            ]
        },
    )
    assert nova.status_code == 200, nova.text
    assert [item["id"] for item in nova.json()] == [
        pergunta_c["id"],
        pergunta_a["id"],
        pergunta_b["id"],
    ]
    assert [item["ordem"] for item in nova.json()] == [1, 2, 3]

    de_novo = client.post(
        f"/pesquisas/{pid}/perguntas/reordenar",
        headers=headers,
        json={
            "pergunta_ids": [
                pergunta_c["id"],
                pergunta_a["id"],
                pergunta_b["id"],
            ]
        },
    )
    assert [item["id"] for item in de_novo.json()] == [
        pergunta_c["id"],
        pergunta_a["id"],
        pergunta_b["id"],
    ]
    assert [item["ordem"] for item in de_novo.json()] == [1, 2, 3]
