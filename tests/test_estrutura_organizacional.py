"""Estrutura organizacional: cargo, setor e hierarquia sem ciclo."""

from sqlalchemy import select

from app.integrations.cnpj import DadosCnpj
from app.integrations.email import caixa_email
from app.models.estrutura import PerfilFuncionario
from tests.contas import SENHA_FUNC, abrir_consultora


def _cnpj_falso(cnpj: str) -> DadosCnpj:
    digitos = "".join(ch for ch in cnpj if ch.isdigit())
    if digitos == "00000000000191":
        return DadosCnpj(
            cnpj="00000000000191",
            razao_social="Camara Exemplo",
            nome_fantasia="Camara",
            municipio="Goiania",
            uf="GO",
        )
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
            "vinculo_titulo": "Estrutura",
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


def test_cargo_cria_e_nao_duplica(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    cargo = client.post(
        f"/projetos/{projeto_id}/cargos",
        headers=headers,
        json={"nome": "Analista"},
    )
    assert cargo.status_code == 200
    repetido = client.post(
        f"/projetos/{projeto_id}/cargos",
        headers=headers,
        json={"nome": "Analista"},
    )
    assert repetido.status_code == 409
    lista = client.get(f"/projetos/{projeto_id}/cargos", headers=headers).json()
    assert len(lista) == 1
    assert lista[0]["nome"] == "Analista"


def test_perfil_com_setor_cargo_e_superior(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    setor = client.post(
        f"/projetos/{projeto_id}/setores",
        headers=headers,
        json={"nome": "Recursos Humanos"},
    ).json()
    cargo = client.post(
        f"/projetos/{projeto_id}/cargos",
        headers=headers,
        json={"nome": "Gerente"},
    ).json()
    gerente_email = "gerente@prefeitura.dev"
    _funcionario(client, headers, projeto_id, gerente_email, "Gerente")
    gerente_id = _usuario_id(client, headers, projeto_id, gerente_email)
    perfil = client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={
            "usuario_id": gerente_id,
            "setor_id": setor["id"],
            "cargo_id": cargo["id"],
        },
    )
    assert perfil.status_code == 200

    func_email = "func@prefeitura.dev"
    _funcionario(client, headers, projeto_id, func_email, "Funcionario")
    func_id = _usuario_id(client, headers, projeto_id, func_email)
    subordinado = client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={
            "usuario_id": func_id,
            "setor_id": setor["id"],
            "cargo_id": cargo["id"],
            "superior_id": gerente_id,
        },
    )
    assert subordinado.status_code == 200

    perfil_db = db.scalar(
        select(PerfilFuncionario).where(
            PerfilFuncionario.projeto_id == projeto_id,
            PerfilFuncionario.usuario_id == func_id,
        )
    )
    assert perfil_db is not None
    assert perfil_db.superior_id == gerente_id
    assert perfil_db.setor_id == setor["id"]
    assert perfil_db.cargo_id == cargo["id"]

    arvore = client.get(f"/projetos/{projeto_id}/arvore", headers=headers).json()
    assert len(arvore) == 1
    assert arvore[0]["usuario_id"] == gerente_id
    assert arvore[0]["cargo"] == "Gerente"
    assert arvore[0]["setor"] == "Recursos Humanos"
    assert arvore[0]["subordinados"][0]["usuario_id"] == func_id
    assert arvore[0]["subordinados"][0]["cargo"] == "Gerente"


def test_hierarquia_rejeita_ciclo(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    a_email = "a@prefeitura.dev"
    b_email = "b@prefeitura.dev"
    _funcionario(client, headers, projeto_id, a_email, "Ana")
    _funcionario(client, headers, projeto_id, b_email, "Bruno")
    a_id = _usuario_id(client, headers, projeto_id, a_email)
    b_id = _usuario_id(client, headers, projeto_id, b_email)
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": a_id, "superior_id": b_id},
    )
    ciclo = client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": b_id, "superior_id": a_id},
    )
    assert ciclo.status_code == 422
    assert "ciclo" in ciclo.json()["detail"].lower()


def test_hierarquia_rejeita_auto_superior(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    email = "auto@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Auto")
    usuario_id = _usuario_id(client, headers, projeto_id, email)
    erro = client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": usuario_id, "superior_id": usuario_id},
    )
    assert erro.status_code == 422


def test_hierarquia_rejeita_ciclo_de_tres(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    _funcionario(client, headers, projeto_id, "a@prefeitura.dev", "Ana")
    _funcionario(client, headers, projeto_id, "b@prefeitura.dev", "Bruno")
    _funcionario(client, headers, projeto_id, "c@prefeitura.dev", "Carla")
    a_id = _usuario_id(client, headers, projeto_id, "a@prefeitura.dev")
    b_id = _usuario_id(client, headers, projeto_id, "b@prefeitura.dev")
    c_id = _usuario_id(client, headers, projeto_id, "c@prefeitura.dev")
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": a_id, "superior_id": b_id},
    )
    client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": b_id, "superior_id": c_id},
    )
    ciclo = client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": c_id, "superior_id": a_id},
    )
    assert ciclo.status_code == 422
    assert "ciclo" in ciclo.json()["detail"].lower()


def test_superior_de_outro_projeto_nao_entra(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    _funcionario(client, headers, projeto_id, "ana@prefeitura.dev", "Ana")
    ana_id = _usuario_id(client, headers, projeto_id, "ana@prefeitura.dev")
    rotulo = client.get("/projetos/rotulos", headers=headers).json()[0]["id"]
    outro = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": rotulo,
            "cnpj": "00000000000191",
            "email_orgao": "outro@camara.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Outro",
        },
    )
    assert outro.status_code == 200, outro.text
    outro_id = outro.json()["id"]
    _funcionario(client, headers, outro_id, "bruno@camara.dev", "Bruno")
    bruno_id = _usuario_id(client, headers, outro_id, "bruno@camara.dev")
    erro = client.put(
        f"/projetos/{projeto_id}/perfis",
        headers=headers,
        json={"usuario_id": ana_id, "superior_id": bruno_id},
    )
    assert erro.status_code == 404
    vazou = db.scalar(
        select(PerfilFuncionario).where(
            PerfilFuncionario.projeto_id == projeto_id,
            PerfilFuncionario.usuario_id == bruno_id,
        )
    )
    assert vazou is None


def test_cargo_nao_existe_em_outro_projeto(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    cargo = client.post(
        f"/projetos/{projeto_id}/cargos",
        headers=headers,
        json={"nome": "Analista"},
    ).json()
    outro = client.post(
        "/projetos",
        headers=headers,
        json={
            "rotulo_id": client.get(
                "/projetos/rotulos", headers=headers
            ).json()[0]["id"],
            "cnpj": "00000000000191",
            "email_orgao": "outro@camara.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Outro",
        },
    )
    assert outro.status_code == 200, outro.text
    outro_id = outro.json()["id"]
    email = "x@prefeitura.dev"
    _funcionario(client, headers, projeto_id, email, "Xavier")
    usuario_id = _usuario_id(client, headers, projeto_id, email)
    erro = client.put(
        f"/projetos/{outro_id}/perfis",
        headers=headers,
        json={"usuario_id": usuario_id, "cargo_id": cargo["id"]},
    )
    # O cargo existe, mas não neste projeto. O funcionário também não está lá.
    assert erro.status_code == 422
