"""Fase 2: obrigatórias (T8), checkbox multi (T9), rate limit (T10)."""

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.pesquisa import Resposta
from app.services.pesquisa import RESPONDER_MAX_TENTATIVAS
from tests.contas import SENHA_FUNC, abrir_consultora


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia=None,
        municipio="Brasilia",
        uf="DF",
    )


def _token_email(destino: str) -> str:
    return next(
        item["corpo"].strip().split()[-1]
        for item in caixa_email.mensagens
        if item["destino"] == destino
    )


def _entrar(client, destino: str, senha: str) -> dict[str, str]:
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": _token_email(destino), "senha": senha},
    )
    assert acesso.status_code == 200
    return {"Authorization": f"Bearer {acesso.json()['access_token']}"}


def _cenario(client, monkeypatch, *, com_checkbox: bool = False):
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
    convite = client.post(
        "/auth/convites",
        headers=headers,
        json={
            "nome": "Servidor",
            "email": "servidor@prefeitura.dev",
            "papel": "FUNCIONARIO",
            "projeto_id": projeto_id,
        },
    )
    assert convite.status_code == 200
    func = _entrar(client, "servidor@prefeitura.dev", SENHA_FUNC)

    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima 2026", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    obrigatoria = client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Nota do clima", "tipo": "NOTA_5", "obrigatoria": True},
    ).json()
    extra = None
    if com_checkbox:
        extra = client.post(
            f"/pesquisas/{pid}/perguntas",
            headers=headers,
            json={
                "texto": "Quais benefícios?",
                "tipo": "CHECKBOX",
                "obrigatoria": True,
                "opcoes": [
                    {"texto": "A"},
                    {"texto": "B"},
                    {"texto": "C"},
                ],
            },
        ).json()
    client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    token = client.post(
        f"/pesquisas/{pid}/tokens",
        headers=headers,
        params={"quantidade": 1},
    ).json()["tokens"][0]
    return headers, pid, token, func, obrigatoria, extra


def test_t8_faltando_obrigatoria_422(client, monkeypatch) -> None:
    headers, pid, token, func, obrigatoria, _extra = _cenario(
        client, monkeypatch, com_checkbox=True
    )
    # Envia só a nota; omite o checkbox obrigatório
    falha = client.post(
        f"/responder/{token}",
        headers=func,
        json={
            "respostas": [
                {"pergunta_id": obrigatoria["id"], "valor_numerico": 4},
            ]
        },
    )
    assert falha.status_code == 422
    detalhe = falha.json()["detail"].lower()
    assert "faltam" in detalhe or "obrigat" in detalhe
    assert "benef" in detalhe or "quais" in detalhe
    # painel ainda sem respostas de participante
    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers)
    assert painel.json()[0]["respostas"] == 0


def test_t9_checkbox_tres_opcoes_um_participante(client, monkeypatch, db) -> None:
    headers, pid, token, func, obrigatoria, checkbox = _cenario(
        client, monkeypatch, com_checkbox=True
    )
    assert checkbox is not None
    opcoes = [item["id"] for item in checkbox["opcoes"]]
    assert len(opcoes) == 3

    envio = client.post(
        f"/responder/{token}",
        headers=func,
        json={
            "respostas": [
                {"pergunta_id": obrigatoria["id"], "valor_numerico": 5},
                {"pergunta_id": checkbox["id"], "opcao_ids": opcoes},
            ]
        },
    )
    assert envio.status_code == 200

    db.expire_all()
    linhas = (
        db.query(Resposta).filter(Resposta.pergunta_id == checkbox["id"]).all()
    )
    assert len(linhas) == 3

    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers)
    assert painel.status_code == 200
    bloco = next(item for item in painel.json() if item["pergunta_id"] == checkbox["id"])
    assert bloco["respostas"] == 1
    assert bloco["contagem_opcoes"] is not None
    totais = {item["opcao_id"]: item["total"] for item in bloco["contagem_opcoes"]}
    assert totais[opcoes[0]] == 1
    assert totais[opcoes[1]] == 1
    assert totais[opcoes[2]] == 1


def test_t10_rate_limit_429(client, monkeypatch) -> None:
    _headers, _pid, token, func, obrigatoria, _extra = _cenario(client, monkeypatch)
    # Tentativas inválidas (sem corpo útil) para não concluir a pesquisa
    ultimo = None
    for _ in range(RESPONDER_MAX_TENTATIVAS):
        ultimo = client.post(
            f"/responder/{token}",
            headers=func,
            json={"respostas": []},
        )
        assert ultimo.status_code == 422
    bloqueado = client.post(
        f"/responder/{token}",
        headers=func,
        json={
            "respostas": [
                {"pergunta_id": obrigatoria["id"], "valor_numerico": 3},
            ]
        },
    )
    assert bloqueado.status_code == 429
    assert "tentativas" in bloqueado.json()["detail"].lower()
