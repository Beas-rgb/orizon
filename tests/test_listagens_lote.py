"""Listagens que não podem consultar o banco uma pessoa por vez."""

from sqlalchemy import event

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from tests.contas import SENHA_FUNC, abrir_consultora


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
            "vinculo_titulo": "Equipe",
        },
    )
    return headers, projeto.json()["id"]


def _aceitar(client, headers, projeto_id: str, email: str, nome: str) -> None:
    client.post(
        "/auth/convites",
        headers=headers,
        json={
            "projeto_id": projeto_id,
            "email": email,
            "papel": "FUNCIONARIO",
            "nome": nome,
        },
    )
    corpo = next(
        item["corpo"]
        for item in reversed(caixa_email.mensagens)
        if item["destino"] == email
    )
    token = corpo.strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": SENHA_FUNC},
    )
    assert acesso.status_code == 200


def test_equipe_pagina_sem_consulta_por_pessoa(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    for i, nome in enumerate(("Ana", "Bruno", "Carla"), start=1):
        _aceitar(client, headers, projeto_id, f"p{i}@prefeitura.dev", nome)

    primeira = client.get(
        f"/projetos/{projeto_id}/equipe?limite=1",
        headers=headers,
    )
    assert primeira.status_code == 200
    assert len(primeira.json()) == 1
    segunda = client.get(
        f"/projetos/{projeto_id}/equipe?limite=1&deslocamento=1",
        headers=headers,
    )
    assert segunda.json()[0]["email"] != primeira.json()[0]["email"]

    sqls: list[str] = []

    def ouvir(_conn, _cursor, statement, _params, _context, _executemany) -> None:
        sqls.append(statement)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", ouvir)
    try:
        cheia = client.get(
            f"/projetos/{projeto_id}/equipe?limite=100",
            headers=headers,
        )
    finally:
        event.remove(engine, "before_cursor_execute", ouvir)
    assert cheia.status_code == 200
    assert len(cheia.json()) >= 3
    de_usuario = [s for s in sqls if "usuarios" in s.lower()]
    assert any(" in " in s.lower() for s in de_usuario)
    individuais = [
        s
        for s in de_usuario
        if " in " not in s.lower() and " usu" in s.lower()
    ]
    assert len(individuais) <= 2
