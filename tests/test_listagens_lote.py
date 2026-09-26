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


def _id(client, headers, projeto_id: str, email: str) -> str:
    equipe = client.get(
        f"/projetos/{projeto_id}/equipe?limite=100",
        headers=headers,
    ).json()
    return next(item["id"] for item in equipe if item["email"] == email)


def _contar(engine, caminho: str, client, headers) -> tuple[int, list[str]]:
    sqls: list[str] = []

    def ouvir(_c, _cur, statement, _p, _ctx, _ex) -> None:
        sqls.append(statement)

    event.listen(engine, "before_cursor_execute", ouvir)
    try:
        resp = client.get(caminho, headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", ouvir)
    assert resp.status_code == 200
    return resp.status_code, sqls


def test_participantes_pagina_e_clima_sem_nome(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    for i, nome in enumerate(("Ana", "Bruno", "Carla"), start=1):
        _aceitar(client, headers, projeto_id, f"f{i}@prefeitura.dev", nome)
    clima = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima", "tipo": "CLIMA"},
    ).json()
    agregado = client.get(
        f"/pesquisas/{clima['id']}/participantes?limite=1",
        headers=headers,
    )
    assert agregado.status_code == 200
    assert agregado.json()["agregado"] is True
    assert agregado.json()["itens"] is None
    assert agregado.json()["total"] == 3
    assert "f1@prefeitura.dev" not in agregado.text

    desempenho = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Nota", "tipo": "DESEMPENHO"},
    ).json()
    pagina = client.get(
        f"/pesquisas/{desempenho['id']}/participantes?limite=1",
        headers=headers,
    )
    assert pagina.status_code == 200
    assert pagina.json()["total"] == 3
    assert len(pagina.json()["itens"]) == 1
    _, sqls = _contar(
        db.get_bind(),
        f"/pesquisas/{desempenho['id']}/participantes?limite=100",
        client,
        headers,
    )
    de_usuario = [s for s in sqls if "usuarios" in s.lower()]
    assert any(" in " in s.lower() for s in de_usuario)


def test_arvore_le_pessoas_de_uma_vez(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    ids = []
    for i, nome in enumerate(("Ana", "Bruno", "Carla", "Dora"), start=1):
        email = f"a{i}@prefeitura.dev"
        _aceitar(client, headers, projeto_id, email, nome)
        ids.append(_id(client, headers, projeto_id, email))
    for filho, pai in zip(ids[1:], ids[:-1], strict=True):
        perfil = client.put(
            f"/projetos/{projeto_id}/perfis",
            headers=headers,
            json={"usuario_id": filho, "superior_id": pai},
        )
        assert perfil.status_code == 200, perfil.text
    _, sqls = _contar(
        db.get_bind(),
        f"/projetos/{projeto_id}/arvore",
        client,
        headers,
    )
    de_usuario = [s for s in sqls if "usuarios" in s.lower()]
    assert any(" in " in s.lower() for s in de_usuario)
    individuais = [s for s in de_usuario if " in " not in s.lower()]
    assert len(individuais) <= 3

