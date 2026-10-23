"""CLIMA sem horário individual. O desempenho conserva o carimbo."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from app.models.auditoria import LogAuditoria
from app.models.base import agora
from app.models.pesquisa import (
    Pesquisa,
    PesquisaParticipante,
    Resposta,
    TokenResposta,
)
from tests.contas import SENHA_FUNC, abrir_consultora
from tests.test_anonimato_clima import _cnpj_falso, _entrar, _projeto_clima


def _publicar_clima(client, monkeypatch, emails: list[str]):
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    headers = abrir_consultora(client, email="tia-clima@horizon.dev", nome="Tia Clima")
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    projeto = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "rh-hora@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Clima sem hora",
        },
    )
    projeto_id = projeto.json()["id"]
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    acessos = []
    for indice, email in enumerate(emails):
        client.post(
            "/auth/convites",
            headers=headers,
            json={
                "projeto_id": projeto_id,
                "email": email,
                "papel": "FUNCIONARIO",
                "nome": f"Pessoa {indice}",
            },
        )
        acessos.append(_entrar(client, email, SENHA_FUNC))
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima sem hora", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    pergunta = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Nota?", "tipo": "NOTA_5"},
    ).json()["id"]
    assert client.post(f"/pesquisas/{pid}/publicar", headers=headers).status_code == 200
    return headers, acessos, pid, pergunta


def _responder(client, acesso, pid, pergunta, nota: int) -> None:
    envio = client.post(
        f"/eu/pesquisas/{pid}/responder",
        headers=acesso,
        json={"respostas": [{"pergunta_id": pergunta, "valor_numerico": nota}]},
    )
    assert envio.status_code == 200, envio.text


def _e_meia_noite(valor: datetime) -> bool:
    base = valor if valor.tzinfo else valor.replace(tzinfo=UTC)
    return base.hour == 0 and base.minute == 0 and base.second == 0


def test_join_por_horario_nao_liga_nota_e_email(client, monkeypatch, db) -> None:
    """1. Cinco notas diferentes não se ligam ao e-mail pelo horário."""
    emails = [f"p{i}@hora.dev" for i in range(5)]
    _headers, acessos, pid, pergunta = _publicar_clima(client, monkeypatch, emails)
    for acesso, nota in zip(acessos, range(1, 6), strict=True):
        client.get(f"/eu/pesquisas/{pid}/formulario", headers=acesso)
        _responder(client, acesso, pid, pergunta, nota)
    db.expire_all()
    ligados = db.execute(
        text(
            """
            SELECT u.email, r.valor_numerico
            FROM pesquisa_participantes p
            JOIN usuarios u ON u.id = p.usuario_id
            JOIN respostas r ON r.respondido_em = p.respondido_em
            WHERE p.pesquisa_id = :pid
            """
        ),
        {"pid": pid},
    ).all()
    assert ligados == []


def test_pessoa_em_outro_dia_nao_se_isola(client, monkeypatch, db) -> None:
    """2. Responder noutro dia não cria coluna que isole a pessoa."""
    _headers, acessos, pid, pergunta = _publicar_clima(
        client, monkeypatch, ["a@hora.dev", "b@hora.dev"]
    )
    _responder(client, acessos[0], pid, pergunta, 1)
    futuro = agora() + timedelta(days=3, hours=5)
    monkeypatch.setattr("app.services.pesquisa.resposta.agora", lambda: futuro)
    monkeypatch.setattr("app.services.pesquisa.crud.agora", lambda: futuro)
    monkeypatch.setattr("app.services.auditoria.agora", lambda: futuro)
    _responder(client, acessos[1], pid, pergunta, 5)
    db.expire_all()
    respostas = db.scalars(
        select(Resposta)
        .join(TokenResposta, TokenResposta.id == Resposta.token_id)
        .where(TokenResposta.pesquisa_id == pid)
    ).all()
    tokens = db.scalars(
        select(TokenResposta).where(TokenResposta.pesquisa_id == pid)
    ).all()
    partes = db.scalars(
        select(PesquisaParticipante).where(PesquisaParticipante.pesquisa_id == pid)
    ).all()
    assert len({item.respondido_em for item in respostas}) == 1
    assert len({item.criado_em for item in tokens}) == 1
    assert all(item.usado_em is None for item in tokens)
    assert all(item.iniciado_em is None for item in partes)
    assert all(item.respondido_em is None for item in partes)


def test_ids_nao_seguem_a_ordem_de_envio(client, monkeypatch, db) -> None:
    """3. uuid4 e a data fixa não devolvem a ordem dos participantes."""
    import uuid

    _headers, acessos, pid, pergunta = _publicar_clima(
        client, monkeypatch, [f"o{i}@hora.dev" for i in range(4)]
    )
    for acesso, nota in zip(acessos, (1, 2, 3, 4), strict=True):
        _responder(client, acesso, pid, pergunta, nota)
    db.expire_all()
    ids = db.scalars(
        select(Resposta.id)
        .join(TokenResposta, TokenResposta.id == Resposta.token_id)
        .where(TokenResposta.pesquisa_id == pid)
        .order_by(Resposta.respondido_em, Resposta.id)
    ).all()
    assert len(ids) == 4
    assert all(uuid.UUID(item).version == 4 for item in ids)
    horas = db.scalars(
        select(Resposta.respondido_em)
        .join(TokenResposta, TokenResposta.id == Resposta.token_id)
        .where(TokenResposta.pesquisa_id == pid)
    ).all()
    publicados = db.get(Pesquisa, pid)
    assert publicados is not None and publicados.publicada_em is not None
    assert all(_e_meia_noite(item) for item in horas)
    assert {item.date() for item in horas} == {publicados.publicada_em.date()}


def test_participante_de_clima_fica_sem_carimbo(client, monkeypatch, db) -> None:
    """4. Depois do envio, o participante não guarda hora nem token pessoal."""
    headers, func, pid = _projeto_clima(client, monkeypatch, "so@hora.dev")
    formulario = client.get(f"/eu/pesquisas/{pid}/formulario", headers=func)
    pergunta = formulario.json()[0]["id"]
    antes = db.scalar(
        select(PesquisaParticipante).where(PesquisaParticipante.pesquisa_id == pid)
    )
    assert antes is not None
    criado = antes.criado_em
    pessoal = antes.token_id
    _responder(client, func, pid, pergunta, 3)
    db.expire_all()
    parte = db.get(PesquisaParticipante, antes.id)
    assert parte is not None
    assert parte.iniciado_em is None
    assert parte.respondido_em is None
    assert parte.atualizado_em == criado
    assert parte.token_id is None
    assert pessoal is None or db.get(TokenResposta, pessoal) is None
    assert headers


def test_auditoria_de_clima_nao_tem_hora_de_envio(client, monkeypatch, db) -> None:
    """5. O log do clima não carimba o instante do envio."""
    _headers, func, pid = _projeto_clima(client, monkeypatch, "log@hora.dev")
    formulario = client.get(f"/eu/pesquisas/{pid}/formulario", headers=func)
    pergunta = formulario.json()[0]["id"]
    _responder(client, func, pid, pergunta, 2)
    db.expire_all()
    logs = db.scalars(
        select(LogAuditoria).where(LogAuditoria.acao == "PESQUISA_RESPONDIDA")
    ).all()
    assert logs
    assert all(item.usuario_id is None for item in logs)
    pesquisa = db.get(Pesquisa, pid)
    assert pesquisa is not None
    assert all(_e_meia_noite(item.criado_em) for item in logs)
    assert {item.criado_em.date() for item in logs} == {pesquisa.publicada_em.date()}


def test_limpeza_reescreve_horario_antigo_de_clima(client, monkeypatch, db) -> None:
    """Horário antigo de clima vira a meia-noite da publicação."""
    from app.services.pesquisa.horario_clima import limpar_horarios_clima

    _headers, func, pid = _projeto_clima(client, monkeypatch, "velho@hora.dev")
    formulario = client.get(f"/eu/pesquisas/{pid}/formulario", headers=func)
    pergunta = formulario.json()[0]["id"]
    _responder(client, func, pid, pergunta, 4)
    db.expire_all()
    resposta = db.scalar(
        select(Resposta)
        .join(TokenResposta, TokenResposta.id == Resposta.token_id)
        .where(TokenResposta.pesquisa_id == pid)
    )
    token = db.get(TokenResposta, resposta.token_id)
    assert resposta is not None and token is not None
    antigo = datetime(2024, 3, 3, 15, 4, tzinfo=UTC)
    resposta.respondido_em = antigo
    token.criado_em = antigo
    token.usado_em = antigo
    db.commit()
    limpar_horarios_clima(db)
    db.commit()
    db.expire_all()
    de_novo = db.get(Resposta, resposta.id)
    token_de_novo = db.get(TokenResposta, token.id)
    pesquisa = db.get(Pesquisa, pid)
    assert de_novo is not None and token_de_novo is not None and pesquisa is not None
    assert _e_meia_noite(de_novo.respondido_em)
    assert de_novo.respondido_em.date() == pesquisa.publicada_em.date()
    assert _e_meia_noite(token_de_novo.criado_em)
    assert token_de_novo.usado_em is None
