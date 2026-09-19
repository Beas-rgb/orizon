"""P1: hash de tokens, JWT com sessão, link só fora de production."""

from sqlalchemy import select

from app.core.tokens import hash_token
from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.pesquisa import TokenResposta
from tests.contas import SENHA, SENHA_FUNC, abrir_consultora


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


def test_token_resposta_so_hash_no_banco(client, monkeypatch, db):
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
            "email_orgao": "rh-p1@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital P1",
        },
    ).json()
    client.patch(
        f"/projetos/{projeto['id']}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    client.post(
        "/auth/convites",
        headers=headers,
        json={
            "projeto_id": projeto["id"],
            "email": "func-p1@orgao.dev",
            "papel": "FUNCIONARIO",
            "nome": "Func P1",
        },
    )
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": _token_email("func-p1@orgao.dev"), "senha": SENHA_FUNC},
    )
    func = {"Authorization": f"Bearer {acesso.json()['access_token']}"}
    pid = client.post(
        f"/projetos/{projeto['id']}/pesquisas",
        headers=headers,
        json={"titulo": "P1 hash", "tipo": "CLIMA"},
    ).json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Ok?", "tipo": "NOTA_5"},
    )
    assert client.post(f"/pesquisas/{pid}/publicar", headers=headers).status_code == 200
    plain = client.post(f"/pesquisas/{pid}/tokens", headers=headers).json()["tokens"][0]
    linha = db.scalar(
        select(TokenResposta).where(TokenResposta.token_hash == hash_token(plain))
    )
    assert linha is not None
    assert plain not in linha.token_hash
    assert len(linha.token_hash) == 64
    assert client.get(f"/responder/{plain}", headers=func).status_code == 200


def test_access_morre_apos_sair(client):
    headers = abrir_consultora(client)
    email = client.get("/auth/eu", headers=headers).json()["email"]
    entrada = client.post("/auth/login", json={"email": email, "senha": SENHA})
    assert entrada.status_code == 200
    access = entrada.json()["access_token"]
    refresh = entrada.json()["refresh_token"]
    auth = {"Authorization": f"Bearer {access}"}
    assert client.get("/auth/eu", headers=auth).status_code == 200
    assert client.post("/auth/sair", json={"refresh_token": refresh}).status_code == 200
    assert client.get("/auth/eu", headers=auth).status_code == 401


def test_link_primeiro_acesso_ausente_em_production(client, monkeypatch):
    headers = abrir_consultora(client)
    monkeypatch.setattr("app.core.config.settings.app_env", "production")
    monkeypatch.setattr("app.services.identidade.settings.app_env", "production")
    monkeypatch.setattr(
        "app.integrations.email.caixa_email.enviar",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("smtp down")),
    )
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_falso)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")
    criado = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "19131243000197",
            "email_orgao": "prod-link@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Edital prod",
        },
    )
    assert criado.status_code == 200
    assert not criado.json().get("link_primeiro_acesso")
