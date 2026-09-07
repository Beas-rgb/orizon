from app.integrations.email import caixa_email
from app.models.usuario import Usuario
from app.services.notificacao import reservar_telefone

SENHA = "senha-segura-1"


def _projeto(client, monkeypatch) -> tuple[dict[str, str], str]:
    from app.integrations.cnpj import DadosCnpj

    monkeypatch.setattr(
        "app.services.projeto.buscar",
        lambda _cnpj: DadosCnpj(
            cnpj="19131243000197",
            razao_social="Prefeitura Exemplo",
            nome_fantasia=None,
            municipio="Brasilia",
            uf="DF",
        ),
    )
    criado = client.post(
        "/auth/bootstrap",
        json={"nome": "Tia", "email": "tia@horizon.dev", "senha": SENHA},
    )
    headers = {"Authorization": f"Bearer {criado.json()['access_token']}"}
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
            "vinculo_titulo": "Edital 1",
        },
    )
    return headers, projeto.json()["id"]


def test_convite_grava_entrega_sem_token(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    entregas = client.get(
        f"/projetos/{projeto_id}/entregas",
        headers=headers,
    )
    assert entregas.status_code == 200
    item = entregas.json()[0]
    assert item["canal"] == "EMAIL"
    assert item["status"] == "ENVIADO"
    assert item["destino"] == "rh@prefeitura.dev"
    assert "token" not in item["assunto"].lower()
    assert caixa_email.mensagens[-1]["destino"] == "rh@prefeitura.dev"

    token = caixa_email.mensagens[-1]["corpo"].strip().split()[-1]
    acesso = client.post(
        "/auth/primeiro-acesso",
        json={"token": token, "senha": "senha-orgao-1"},
    )
    orgao = {"Authorization": f"Bearer {acesso.json()['access_token']}"}
    negado = client.get(f"/projetos/{projeto_id}/entregas", headers=orgao)
    assert negado.status_code == 404


def test_resposta_avisa_consultora_sem_nome(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    client.patch(
        f"/projetos/{projeto_id}/configuracao",
        headers=headers,
        json={"pesquisas_habilitadas": True},
    )
    pesquisa = client.post(
        f"/projetos/{projeto_id}/pesquisas",
        headers=headers,
        json={"titulo": "Clima 2026", "tipo": "CLIMA"},
    )
    pid = pesquisa.json()["id"]
    client.post(
        f"/pesquisas/{pid}/perguntas",
        headers=headers,
        json={"texto": "Como está o ambiente?", "tipo": "NOTA_5"},
    )
    client.post(f"/pesquisas/{pid}/publicar", headers=headers)
    token = client.post(
        f"/pesquisas/{pid}/tokens",
        headers=headers,
        params={"quantidade": 1},
    ).json()["tokens"][0]
    pergunta_id = client.get(f"/responder/{token}").json()[0]["id"]
    client.post(
        f"/responder/{token}",
        json={"respostas": [{"pergunta_id": pergunta_id, "valor_numerico": 4}]},
    )

    avisos = client.get("/notificacoes", headers=headers)
    assert avisos.status_code == 200
    aviso = avisos.json()[0]
    assert aviso["titulo"] == "Nova resposta"
    assert token not in aviso["mensagem"]
    assert "rh@" not in aviso["mensagem"]

    lida = client.post(f"/notificacoes/{aviso['id']}/lida", headers=headers)
    assert lida.status_code == 200
    assert lida.json()["lida"] is True


def test_telefone_nao_envia(db) -> None:
    usuario = Usuario(
        nome="Tia",
        email="tia@horizon.dev",
        telefone="61999990000",
        papel="CONSULTOR",
        ativo=True,
    )
    db.add(usuario)
    db.flush()
    entrega = reservar_telefone(
        db,
        usuario.telefone or "",
        "Aviso",
        "SISTEMA",
        None,
        usuario.id,
    )
    db.commit()
    assert entrega.canal == "TELEFONE"
    assert entrega.status == "NAO_HABILITADO"
    assert caixa_email.mensagens == []
