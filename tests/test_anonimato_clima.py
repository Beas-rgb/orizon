"""P0: anonimato CLIMA — participantes agregados, k-anonimato, token sem usuário."""

from sqlalchemy import select

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.auditoria import LogAuditoria
from app.models.pesquisa import PesquisaParticipante, Resposta, TokenResposta
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


def _projeto_clima(client, monkeypatch, email_func: str = "anon@orgao.dev"):
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
            "email_orgao": "rh-anon@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital anon",
        },
    )
    projeto_id = projeto.json()["id"]
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    client.post(
        "/auth/convites",
        headers=headers,
        json={
            "projeto_id": projeto_id,
            "email": email_func,
            "papel": "FUNCIONARIO",
            "nome": "Func Anon",
        },
    )
    func = _entrar(client, email_func, SENHA_FUNC)
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima anon", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Nota do clima?", "tipo": "NOTA_5"},
    )
    assert client.post(f"/pesquisas/{pid}/publicar", headers=headers).status_code == 200
    return headers, func, pid


def test_participantes_clima_so_agregado(client, monkeypatch):
    headers, _func, pid = _projeto_clima(client, monkeypatch)
    parts = client.get(f"/pesquisas/{pid}/participantes", headers=headers).json()
    assert parts["agregado"] is True
    assert parts["itens"] is None
    assert "nome" not in parts


def test_painel_k_anonimato_n1_suprimido(client, monkeypatch, db):
    headers, func, pid = _projeto_clima(client, monkeypatch, "k1@orgao.dev")
    pergunta_id = client.get(
        f"/eu/pesquisas/{pid}/formulario", headers=func
    ).json()[0]["id"]
    envio = client.post(
        f"/eu/pesquisas/{pid}/responder",
        headers=func,
        json={"respostas": [{"pergunta_id": pergunta_id, "valor_numerico": 2}]},
    )
    assert envio.status_code == 200

    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers).json()
    assert painel[0]["respostas"] == 1
    assert painel[0]["suprimido"] is True
    assert painel[0]["media"] is None

    # Resposta não amarra ao participante (token_id limpo).
    part = db.scalar(
        select(PesquisaParticipante).where(PesquisaParticipante.pesquisa_id == pid)
    )
    assert part is not None
    assert part.status == "RESPONDIDA"
    assert part.token_id is None

    # Token da resposta não é o do participante.
    resp = db.scalar(select(Resposta).where(Resposta.pergunta_id == pergunta_id))
    assert resp is not None
    token_linha = db.get(TokenResposta, resp.token_id)
    assert token_linha is not None
    ligado = db.scalar(
        select(PesquisaParticipante).where(
            PesquisaParticipante.token_id == token_linha.id
        )
    )
    assert ligado is None

    # Auditoria sem usuario_id.
    log = db.scalar(
        select(LogAuditoria)
        .where(LogAuditoria.acao == "PESQUISA_RESPONDIDA")
        .order_by(LogAuditoria.criado_em.desc())
    )
    assert log is not None
    assert log.usuario_id is None
