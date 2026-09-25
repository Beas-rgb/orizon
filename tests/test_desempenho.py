"""Ciclo de avaliação de desempenho: criação, relações e cálculo."""

from sqlalchemy import select

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.desempenho import AvaliacaoRelacionamento
from tests.contas import SENHA_FUNC, abrir_consultora


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia="Prefeitura",
        municipio="Brasilia",
        uf="DF",
    )


def _projeto(client, monkeypatch) -> tuple[dict[str, str], str]:
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
            "email_orgao": "rh@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Desempenho",
        },
    )
    return headers, projeto.json()["id"]


def _funcionario(client, headers, projeto_id: str, email: str, nome: str) -> str:
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
    return acesso.json()["access_token"]


def _usuario_id(client, headers, projeto_id: str, email: str) -> str:
    equipe = client.get(f"/projetos/{projeto_id}/equipe", headers=headers).json()
    return next(item["id"] for item in equipe if item["email"] == email)


def test_ciclo_cria_com_escopo_e_pesos(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={
            "nome": "Avaliação 2026",
            "escopo": "ORGANIZACAO",
            "configuracao": (
                '{"pesos": {"AUTO": 1, "SUPERIOR": 2, "SUBORDINADO": 1}, '
                '"ordem": ["AUTO", "SUPERIOR", "SUBORDINADO"]}'
            ),
        },
    )
    assert ciclo.status_code == 200
    dados = ciclo.json()
    assert dados["nome"] == "Avaliação 2026"
    assert dados["escopo"] == "ORGANIZACAO"
    assert dados["status"] == "RASCUNHO"


def test_ciclo_rejeita_config_com_codigo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={
            "nome": "Avaliação 2026",
            "configuracao": '{"eval": "1+1"}',
        },
    )
    assert ciclo.status_code == 422


def test_gerar_relacoes_auto_superior_subordinado(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    gerente_email = "gerente@prefeitura.dev"
    _funcionario(client, headers, projeto_id, gerente_email, "Gerente")
    gerente_id = _usuario_id(client, headers, projeto_id, gerente_email)
    func_email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, func_email, "Funcionario")
    func_id = _usuario_id(client, headers, projeto_id, func_email)
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": func_id, "superior_id": gerente_id},
    )
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    gerar = client.post(
        f"/ciclos/{ciclo['id']}/gerar-relacoes",
        headers=headers,
    )
    assert gerar.status_code == 200
    assert gerar.json()["criados"] == 4  # AUTO, AUTO, SUPERIOR, SUBORDINADO

    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"]
        )
    ).all()
    assert len(relacoes) == 4
    tipos = {r.tipo_relacao for r in relacoes}
    assert tipos == {"AUTO", "SUPERIOR", "SUBORDINADO"}
    superior = next(r for r in relacoes if r.tipo_relacao == "SUPERIOR")
    assert superior.avaliador_id == gerente_id
    assert superior.avaliado_id == func_id


def test_gerar_relacoes_idempotente(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    primeiro = client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    segundo = client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    assert primeiro.json()["criados"] == 1
    assert segundo.json()["criados"] == 1
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"]
        )
    ).all()
    assert len(relacoes) == 1


def test_sem_superior_nao_cria_superior(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"],
            AvaliacaoRelacionamento.tipo_relacao == "SUPERIOR",
        )
    ).all()
    assert len(relacoes) == 0


def test_sem_subordinado_nao_cria_subordinado(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"],
            AvaliacaoRelacionamento.tipo_relacao == "SUBORDINADO",
        )
    ).all()
    assert len(relacoes) == 0


def test_calcular_resultado_com_pesos(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    gerente_email = "gerente@prefeitura.dev"
    _funcionario(client, headers, projeto_id, gerente_email, "Gerente")
    gerente_id = _usuario_id(client, headers, projeto_id, gerente_email)
    func_email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, func_email, "Funcionario")
    func_id = _usuario_id(client, headers, projeto_id, func_email)
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": func_id, "superior_id": gerente_id},
    )
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={
            "nome": "Avaliação 2026",
            "configuracao": '{"pesos": {"AUTO": 1, "SUPERIOR": 2}}',
        },
    ).json()
    client.post(f"/ciclos/{ciclo['id']}/gerar-relacoes", headers=headers)
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo["id"]
        )
    ).all()
    auto = next(
        r for r in relacoes if r.tipo_relacao == "AUTO" and r.avaliado_id == func_id
    )
    superior = next(r for r in relacoes if r.tipo_relacao == "SUPERIOR")
    # Simula respostas: AUTO 4,0 e SUPERIOR 4,5.
    from app.core.tokens import novo_id
    from app.models.base import agora
    from app.models.pesquisa import Resposta

    agora_ = agora()
    db.add(
        Resposta(
            id=novo_id(),
            token_id=auto.id,
            pergunta_id="p1",
            valor_numerico=4,
            respondido_em=agora_,
        )
    )
    db.add(
        Resposta(
            id=novo_id(),
            token_id=superior.id,
            pergunta_id="p1",
            valor_numerico=5,
            respondido_em=agora_,
        )
    )
    db.commit()
    resultado = client.get(
        f"/ciclos/{ciclo['id']}/resultado/{func_id}",
        headers=headers,
    )
    assert resultado.status_code == 200
    dados = resultado.json()
    assert dados["resultado"] == 4.67  # (4*1 + 5*2) / 3
    assert dados["por_perspectiva"]["AUTO"] == 4.0
    assert dados["por_perspectiva"]["SUPERIOR"] == 5.0


def test_relacao_nao_existente_404(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Funcionario")
    ciclo = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Avaliação 2026"},
    ).json()
    outro = client.post(
        f"/projetos/{projeto_id}/ciclos",
        headers=headers,
        json={"nome": "Outro ciclo"},
    ).json()
    resp = client.get(
        f"/ciclos/{ciclo['id']}/relacao/{outro['id']}",
        headers=headers,
    )
    assert resp.status_code == 404
