"""Fase 1: só FUNCIONÁRIO autenticado do projeto responde (T1–T7)."""

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.pesquisa import PesquisaParticipante
from tests.contas import SENHA_FUNC, SENHA_ORGAO, abrir_consultora, abrir_dev


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


def _projeto_com_pesquisa(client, monkeypatch):
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
            "vinculo_titulo": "Edital 1",
        },
    )
    projeto_id = projeto.json()["id"]
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
    return headers, projeto_id, pid, token


def _convidar_funcionario(client, headers, projeto_id: str, email: str):
    convite = client.post(
        "/auth/convites",
        headers=headers,
        json={
            "nome": "Servidor",
            "email": email,
            "papel": "FUNCIONARIO",
            "projeto_id": projeto_id,
        },
    )
    assert convite.status_code == 200
    return _entrar(client, email, SENHA_FUNC)


def test_t6_sem_login_responde_401(client, monkeypatch) -> None:
    _headers, _projeto_id, _pid, token = _projeto_com_pesquisa(client, monkeypatch)
    assert client.get(f"/responder/{token}").status_code == 401
    assert (
        client.post(
            f"/responder/{token}",
            json={"respostas": [{"pergunta_id": "x", "valor_numerico": 3}]},
        ).status_code
        == 401
    )


def test_t1_consultora_com_token_404(client, monkeypatch) -> None:
    headers, _projeto_id, _pid, token = _projeto_com_pesquisa(client, monkeypatch)
    assert client.get(f"/responder/{token}", headers=headers).status_code == 404
    assert (
        client.post(
            f"/responder/{token}",
            headers=headers,
            json={"respostas": [{"pergunta_id": "x", "valor_numerico": 3}]},
        ).status_code
        == 404
    )


def test_t2_orgao_com_token_404(client, monkeypatch) -> None:
    headers, projeto_id, _pid, token = _projeto_com_pesquisa(client, monkeypatch)
    orgao = _entrar(client, "rh@prefeitura.dev", SENHA_ORGAO)
    assert client.get(f"/responder/{token}", headers=orgao).status_code == 404
    assert (
        client.post(
            f"/responder/{token}",
            headers=orgao,
            json={"respostas": [{"pergunta_id": "x", "valor_numerico": 3}]},
        ).status_code
        == 404
    )
    # vínculo do órgão existe no projeto — ainda assim não responde
    assert projeto_id


def test_t3_ti_com_token_404(client, monkeypatch) -> None:
    _headers, _projeto_id, _pid, token = _projeto_com_pesquisa(client, monkeypatch)
    ti = abrir_dev(client)
    assert client.get(f"/responder/{token}", headers=ti).status_code == 404


def test_t4_funcionario_sem_vinculo_404(client, monkeypatch) -> None:
    headers, _projeto_a, _pid, token = _projeto_com_pesquisa(client, monkeypatch)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")

    def _cnpj_b(_cnpj: str) -> DadosCnpj:
        return DadosCnpj(
            cnpj="00000000000191",
            razao_social="Camara",
            nome_fantasia=None,
            municipio="Goiania",
            uf="GO",
        )

    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_b)
    projeto_b = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "00000000000191",
            "email_orgao": "rh@camara.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Outro",
        },
    ).json()["id"]
    # Funcionário só no projeto B — sem vínculo no projeto da pesquisa A
    func_b = _convidar_funcionario(
        client, headers, projeto_b, "servidor-b@camara.dev"
    )
    assert client.get(f"/responder/{token}", headers=func_b).status_code == 404


def test_t5_funcionario_outro_projeto_404(client, monkeypatch) -> None:
    """Mesmo que exista pesquisa A, funcionário só do projeto B não entra."""
    headers, projeto_a, _pid, token = _projeto_com_pesquisa(client, monkeypatch)
    rotulos = client.get("/projetos/rotulos", headers=headers).json()
    clima = next(item for item in rotulos if item["codigo"] == "CLIMA")

    def _cnpj_b(_cnpj: str) -> DadosCnpj:
        return DadosCnpj(
            cnpj="00000000000191",
            razao_social="Camara",
            nome_fantasia=None,
            municipio="Goiania",
            uf="GO",
        )

    monkeypatch.setattr("app.services.projeto.buscar", _cnpj_b)
    projeto_b = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": clima["id"],
            "cnpj": "00000000000191",
            "email_orgao": "rh@camara.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Projeto B",
        },
    ).json()["id"]
    func_b = _convidar_funcionario(
        client, headers, projeto_b, "servidor-b@camara.dev"
    )
    assert projeto_a
    assert client.get(f"/responder/{token}", headers=func_b).status_code == 404
    assert (
        client.post(
            f"/responder/{token}",
            headers=func_b,
            json={"respostas": [{"pergunta_id": "x", "valor_numerico": 2}]},
        ).status_code
        == 404
    )


def test_t7_funcionario_correto_responde_e_segunda_vez_409(
    client, monkeypatch, db
) -> None:
    headers, projeto_id, pid, token = _projeto_com_pesquisa(client, monkeypatch)
    func = _convidar_funcionario(
        client, headers, projeto_id, "servidor@prefeitura.dev"
    )
    formulario = client.get(f"/responder/{token}", headers=func)
    assert formulario.status_code == 200
    pergunta_id = formulario.json()[0]["id"]

    envio = client.post(
        f"/responder/{token}",
        headers=func,
        json={"respostas": [{"pergunta_id": pergunta_id, "valor_numerico": 4}]},
    )
    assert envio.status_code == 200
    assert envio.json()["nota"] is None

    db.expire_all()
    participante = (
        db.query(PesquisaParticipante)
        .filter(PesquisaParticipante.pesquisa_id == pid)
        .one()
    )
    assert participante.status == "RESPONDIDA"
    assert participante.respondido_em is not None

    segunda = client.post(
        f"/responder/{token}",
        headers=func,
        json={"respostas": [{"pergunta_id": pergunta_id, "valor_numerico": 5}]},
    )
    assert segunda.status_code == 409
    assert "já respondeu" in segunda.json()["detail"].lower()

    # consultora ainda vê agregado anônimo
    painel = client.get(f"/pesquisas/{pid}/painel", headers=headers)
    assert painel.status_code == 200
    assert painel.json()[0]["respostas"] == 1
    assert "servidor" not in painel.text.lower()
