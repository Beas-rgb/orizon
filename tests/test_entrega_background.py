"""Entrega de e-mail fora do request, no mesmo banco do ambiente."""

from sqlalchemy import select

from app.integrations.email import EmailNaoEnviado, caixa_email
from app.models.notificacao import EntregaMensagem
from tests.contas import abrir_consultora
from tests.test_orgao_acesso import (
    _cnpj,
    _criar_projeto,
    _entrar_orgao,
    _rotulo_clima,
)


def _pesquisa_publicavel(client, monkeypatch, email: str):
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    projeto = _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="Entrega bg",
        rotulo_id=rid,
    )
    _entrar_orgao(client, email)
    pid = projeto["id"]
    client.patch(
        f"/projetos/{pid}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{pid}/pesquisas",
        headers=headers,
        json={"titulo": "Aviso background", "tipo": "DESEMPENHO"},
    ).json()
    client.post(
        f"/pesquisas/{pesquisa['id']}/perguntas",
        headers=headers,
        json={"texto": "Como avalia?", "tipo": "NOTA_5"},
    )
    return headers, pesquisa["id"]


def test_publicar_marca_enviado_e_grava_caixa(client, monkeypatch, db) -> None:
    headers, pesquisa_id = _pesquisa_publicavel(
        client, monkeypatch, "bg-ok@prefeitura.dev"
    )
    antes = len(caixa_email.mensagens)
    pub = client.post(f"/pesquisas/{pesquisa_id}/publicar", headers=headers)
    assert pub.status_code == 200
    db.expire_all()
    entrega = db.scalar(
        select(EntregaMensagem).where(
            EntregaMensagem.referencia == "AVISO_NOVA_PESQUISA"
        )
    )
    assert entrega is not None
    assert entrega.status == "ENVIADO"
    assert entrega.erro is None
    novos = caixa_email.mensagens[antes:]
    assert any("nova pesquisa" in item["assunto"].lower() for item in novos)
    assert all("?t=" not in item["corpo"] for item in novos)


def test_provedor_falho_grava_falha_sem_segredo(client, monkeypatch, db) -> None:
    headers, pesquisa_id = _pesquisa_publicavel(
        client, monkeypatch, "bg-falha@prefeitura.dev"
    )

    def explodir(*_args, **_kwargs):
        raise EmailNaoEnviado("password=segredo postgres://interno")

    monkeypatch.setattr(caixa_email, "enviar", explodir)
    pub = client.post(f"/pesquisas/{pesquisa_id}/publicar", headers=headers)
    assert pub.status_code == 200
    db.expire_all()
    entrega = db.scalar(
        select(EntregaMensagem)
        .where(EntregaMensagem.referencia == "AVISO_NOVA_PESQUISA")
        .order_by(EntregaMensagem.criado_em.desc())
    )
    assert entrega is not None
    assert entrega.status == "FALHA"
    assert entrega.erro
    assert "segredo" not in entrega.erro
    assert "postgres" not in entrega.erro.lower()


def test_novo_trabalho_sai_em_background_sem_token(client, monkeypatch, db) -> None:
    monkeypatch.setattr("app.services.projeto.buscar", _cnpj)
    headers = abrir_consultora(client)
    rid = _rotulo_clima(client, headers)
    email = "bg-trabalho@prefeitura.dev"
    _criar_projeto(
        client,
        headers,
        cnpj="19131243000197",
        email=email,
        titulo="Trabalho 1",
        rotulo_id=rid,
    )
    _entrar_orgao(client, email)
    antes = len(caixa_email.mensagens)
    segundo = _criar_projeto(
        client,
        headers,
        cnpj="00000000000191",
        email=email,
        titulo="Trabalho 2",
        rotulo_id=rid,
    )
    assert segundo["id"]
    db.expire_all()
    entrega = db.scalar(
        select(EntregaMensagem).where(
            EntregaMensagem.referencia == "AVISO_NOVO_TRABALHO",
            EntregaMensagem.destino == email,
        )
    )
    assert entrega is not None
    assert entrega.status == "ENVIADO"
    novos = caixa_email.mensagens[antes:]
    assert any("novo trabalho" in item["assunto"].lower() for item in novos)
    assert all("?t=" not in item["corpo"] for item in novos)
