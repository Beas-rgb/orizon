"""Tokens de curta duração para carga (staging)."""

from app.core.config import settings
from app.main import incluir_lab_se_ligado
from scripts.criar_consultor_teste import criar_consultor_teste
from tests.contas import SENHA


def _headers(client, email: str) -> dict[str, str]:
    entrada = client.post(
        "/auth/login",
        json={"email": email, "senha": SENHA},
    )
    assert entrada.status_code == 200
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_tokens_lab_respondem(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    monkeypatch.setattr(settings, "lab_tokens_permitidos", True)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-tok@horizon.dev", SENHA)
    headers = _headers(client, "lab-tok@horizon.dev")
    cid = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Tok",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 8,
            "perfil": "NEUTRO",
        },
    ).json()["id"]
    tokens = client.post(
        f"/lab/cenarios/{cid}/tokens",
        headers=headers,
        params={"quantidade": 2},
    )
    assert tokens.status_code == 200, tokens.text
    lote = tokens.json()
    assert len(lote) == 2
    assert "token" in lote[0]
    pesquisa_id = lote[0]["pesquisa_id"]
    perguntas = client.get(
        f"/eu/pesquisas/{pesquisa_id}/formulario",
        headers={"Authorization": f"Bearer {lote[0]['token']}"},
    )
    assert perguntas.status_code == 200
    assert len(perguntas.json()) >= 1
    # Responde com o token de carga
    pid = perguntas.json()[0]["id"]
    envio = client.post(
        f"/eu/pesquisas/{pesquisa_id}/responder",
        headers={"Authorization": f"Bearer {lote[0]['token']}"},
        json={"respostas": [{"pergunta_id": pid, "valor_numerico": 3}]},
    )
    # formulário tem várias obrigatórias — 422 é auth ok; 200 também
    assert envio.status_code in (200, 422)
    assert envio.status_code != 401
    assert envio.status_code != 404


def test_tokens_lab_sem_flag_404(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    monkeypatch.setattr(settings, "lab_tokens_permitidos", False)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-tok2@horizon.dev", SENHA)
    headers = _headers(client, "lab-tok2@horizon.dev")
    cid = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Tok2",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 9,
            "perfil": "NEUTRO",
        },
    ).json()["id"]
    assert (
        client.post(
            f"/lab/cenarios/{cid}/tokens",
            headers=headers,
            params={"quantidade": 1},
        ).status_code
        == 404
    )
