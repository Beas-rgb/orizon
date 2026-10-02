"""Orçamento curto: /auth/eu em uma consulta; listas no teto da Fase 2."""

from sqlalchemy import event

from tests.contas import SENHA, abrir_dev
from tests.test_cenario_500 import _projeto


def contar(engine, fn):
    sqls: list[str] = []

    def ouvir(_c, _cur, st, _p, _ctx, _ex) -> None:
        sqls.append(st.strip().split()[0].upper())

    event.listen(engine, "before_cursor_execute", ouvir)
    try:
        return fn(), len(sqls)
    finally:
        event.remove(engine, "before_cursor_execute", ouvir)


def test_eu_uma_consulta(client, db) -> None:
    headers = abrir_dev(client, email="uma@horizon.dev")
    resposta, total = contar(
        db.get_bind(),
        lambda: client.get("/auth/eu", headers=headers),
    )
    assert resposta.status_code == 200
    assert total <= 1


def test_listas_no_teto(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    _, total_lista = contar(
        db.get_bind(),
        lambda: client.get("/projetos", headers=headers),
    )
    _, total_um = contar(
        db.get_bind(),
        lambda: client.get(f"/projetos/{projeto_id}", headers=headers),
    )
    assert total_lista <= 6
    assert total_um <= 7


def test_sair_revoga_na_hora(client) -> None:
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Joao", "email": "sai@horizon.dev", "senha": SENHA},
    )
    token = criado.json()["access_token"]
    refresh = criado.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/eu", headers=headers).status_code == 200
    assert client.post("/auth/sair", json={"refresh_token": refresh}).status_code == 200
    assert client.get("/auth/eu", headers=headers).status_code == 401
