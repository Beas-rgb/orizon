"""Importação CSV/XLSX: prévia, validação e confirmação transacional."""

from sqlalchemy import func, select

from app.integrations.cnpj import DadosCnpj
from app.models.estrutura import PerfilFuncionario
from app.models.projeto import ProjetoUsuario
from app.models.usuario import Usuario
from tests.contas import abrir_consultora


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
            "vinculo_titulo": "Importação",
        },
    )
    return headers, projeto.json()["id"]


def _csv(linhas: list[dict[str, str]]) -> bytes:
    cabecalho = "nome;email;cargo;setor;superior_email\n"
    corpo = "\n".join(
        ";".join(
            [
                linha.get("nome", ""),
                linha.get("email", ""),
                linha.get("cargo", ""),
                linha.get("setor", ""),
                linha.get("superior_email", ""),
            ]
        )
        for linha in linhas
    )
    return (cabecalho + corpo).encode("utf-8")


def test_previa_csv_valida_sem_gravar(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    client.post(
        f"/projetos/{projeto_id}/setores",
        headers=headers,
        json={"nome": "Recursos Humanos"},
    )
    client.post(
        f"/projetos/{projeto_id}/cargos",
        headers=headers,
        json={"nome": "Analista"},
    )
    conteudo = _csv(
        [
            {
                "nome": "Ana",
                "email": "ana@prefeitura.dev",
                "cargo": "Analista",
                "setor": "Recursos Humanos",
            },
            {
                "nome": "Bruno",
                "email": "bruno@prefeitura.dev",
                "cargo": "Analista",
                "setor": "Recursos Humanos",
                "superior_email": "ana@prefeitura.dev",
            },
            {
                "nome": "Carlos",
                "email": "carlos@prefeitura.dev",
                "cargo": "Inexistente",
                "setor": "Inexistente",
                "superior_email": "ninguem@prefeitura.dev",
            },
            {
                "nome": "Duplicado",
                "email": "ana@prefeitura.dev",
                "cargo": "Analista",
                "setor": "Recursos Humanos",
            },
        ]
    )
    resp = client.post(
        f"/projetos/{projeto_id}/importar/previa",
        headers=headers,
        files={"arquivo": ("funcionarios.csv", conteudo, "text/csv")},
    )
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["total"] == 4
    assert dados["validos"] == 2
    assert dados["invalidos"] == 2
    assert dados["duplicados"] == 1
    assert dados["superiores_inexistentes"] == 1
    assert dados["setores"] == 2
    assert dados["cargos"] == 2
    assert dados["niveis"] == 2
    # Não gravou nada
    assert db.scalar(select(func.count()).select_from(Usuario)) == 2  # TI + consultora
    assert db.scalar(select(func.count()).select_from(PerfilFuncionario)) == 0


def test_confirmar_grava_so_validos(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    client.post(
        f"/projetos/{projeto_id}/setores",
        headers=headers,
        json={"nome": "Recursos Humanos"},
    )
    client.post(
        f"/projetos/{projeto_id}/cargos",
        headers=headers,
        json={"nome": "Analista"},
    )
    linhas = [
        {
            "nome": "Ana",
            "email": "ana@prefeitura.dev",
            "cargo": "Analista",
            "setor": "Recursos Humanos",
            "superior_email": "",
            "erros": [],
        },
        {
            "nome": "Bruno",
            "email": "bruno@prefeitura.dev",
            "cargo": "Analista",
            "setor": "Recursos Humanos",
            "superior_email": "ana@prefeitura.dev",
            "erros": [],
        },
        {
            "nome": "Erro",
            "email": "invalido",
            "cargo": "",
            "setor": "",
            "superior_email": "",
            "erros": [],
        },
    ]
    resp = client.post(
        f"/projetos/{projeto_id}/importar/confirmar",
        headers=headers,
        json={"linhas": linhas},
    )
    assert resp.status_code == 200
    assert resp.json()["criados"] == 2
    assert resp.json()["total"] == 3
    usuarios = db.scalars(
        select(Usuario).where(Usuario.papel == "FUNCIONARIO")
    ).all()
    assert len(usuarios) == 2
    perfis = db.scalars(
        select(PerfilFuncionario).where(
            PerfilFuncionario.projeto_id == projeto_id
        )
    ).all()
    assert len(perfis) == 2
    ana = next(u for u in usuarios if u.email == "ana@prefeitura.dev")
    bruno = next(u for u in usuarios if u.email == "bruno@prefeitura.dev")
    perfil_bruno = next(p for p in perfis if p.usuario_id == bruno.id)
    assert perfil_bruno.superior_id == ana.id
    vinculos = db.scalars(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.papel == "FUNCIONARIO",
        )
    ).all()
    assert len(vinculos) == 2


def test_confirmacao_revalida_no_servidor(client, monkeypatch, db) -> None:
    """Linha inválida com erros vazios não grava. Erro falso não bloqueia a válida."""
    headers, projeto_id = _projeto(client, monkeypatch)
    linhas = [
        {
            "nome": "Ana",
            "email": "ana@prefeitura.dev",
            "cargo": "Analista",
            "setor": "RH",
            "superior_email": "",
            "erros": [],
        },
        {
            "nome": "Copia",
            "email": "ana@prefeitura.dev",
            "cargo": "Analista",
            "setor": "RH",
            "superior_email": "",
            "erros": [],
        },
        {
            "nome": "Carla",
            "email": "carla@prefeitura.dev",
            "cargo": "Analista",
            "setor": "RH",
            "superior_email": "",
            "erros": ["email inválido"],
        },
    ]
    resp = client.post(
        f"/projetos/{projeto_id}/importar/confirmar",
        headers=headers,
        json={"linhas": linhas},
    )
    assert resp.status_code == 200
    assert resp.json()["criados"] == 2
    emails = {
        u.email
        for u in db.scalars(select(Usuario).where(Usuario.papel == "FUNCIONARIO")).all()
    }
    assert emails == {"ana@prefeitura.dev", "carla@prefeitura.dev"}


def test_importacao_rejeita_html_disfarcado(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    conteudo = b"<html><script>alert(1)</script></html>"
    resp = client.post(
        f"/projetos/{projeto_id}/importar/previa",
        headers=headers,
        files={"arquivo": ("funcionarios.csv", conteudo, "text/csv")},
    )
    assert resp.status_code == 422


def test_importacao_limite_linhas(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    linhas = [
        {
            "nome": f"Func {i}",
            "email": f"func{i}@prefeitura.dev",
            "cargo": "Analista",
            "setor": "RH",
            "superior_email": "",
        }
        for i in range(5001)
    ]
    conteudo = _csv(linhas)
    resp = client.post(
        f"/projetos/{projeto_id}/importar/previa",
        headers=headers,
        files={"arquivo": ("funcionarios.csv", conteudo, "text/csv")},
    )
    assert resp.status_code == 422
    assert "5000" in resp.json()["detail"]


def test_importacao_ciclo_hierarquia(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    conteudo = _csv(
        [
            {
                "nome": "Ana",
                "email": "ana@prefeitura.dev",
                "cargo": "Analista",
                "setor": "RH",
                "superior_email": "bruno@prefeitura.dev",
            },
            {
                "nome": "Bruno",
                "email": "bruno@prefeitura.dev",
                "cargo": "Analista",
                "setor": "RH",
                "superior_email": "ana@prefeitura.dev",
            },
        ]
    )
    resp = client.post(
        f"/projetos/{projeto_id}/importar/previa",
        headers=headers,
        files={"arquivo": ("funcionarios.csv", conteudo, "text/csv")},
    )
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["invalidos"] == 2
    assert any("ciclo" in " ".join(linha["erros"]) for linha in dados["linhas"])


def _funcionario_em_projeto_de(db, consultor_id: str, base_id: str, email: str) -> str:
    from app.core.tokens import novo_id
    from app.models.base import agora
    from app.models.projeto import Projeto

    base = db.get(Projeto, base_id)
    agora_ = agora()
    projeto = Projeto(
        id=novo_id(),
        organizacao_id=base.organizacao_id,
        consultor_id=consultor_id,
        rotulo_id=base.rotulo_id,
        estado="ABERTO",
        vinculo_tipo="EDITAL",
        vinculo_titulo="Outro trabalho",
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )
    pessoa = Usuario(
        id=novo_id(),
        nome=email.split("@")[0],
        email=email,
        papel="FUNCIONARIO",
        tipo_conta="NORMAL",
        ativo=True,
        tentativas_falhas=0,
        criado_em=agora_,
        atualizado_em=agora_,
    )
    db.add_all([projeto, pessoa])
    db.flush()
    db.add(
        ProjetoUsuario(
            id=novo_id(),
            projeto_id=projeto.id,
            usuario_id=pessoa.id,
            papel="FUNCIONARIO",
        )
    )
    db.commit()
    return pessoa.id


def test_importacao_nao_vincula_conta_de_outro_dono(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    consultora = db.scalar(select(Usuario).where(Usuario.email == "tia@horizon.dev"))
    outra = Usuario(
        nome="Outra",
        email="outra@consultoria.dev",
        papel="CONSULTOR",
        tipo_conta="NORMAL",
        ativo=True,
        tentativas_falhas=0,
    )
    db.add(outra)
    db.commit()
    alheio = _funcionario_em_projeto_de(
        db, outra.id, projeto_id, "alheio@outro-orgao.dev"
    )
    proprio = _funcionario_em_projeto_de(
        db, consultora.id, projeto_id, "proprio@prefeitura.dev"
    )
    linhas = [
        {"nome": "TI", "email": "joao@horizon.dev"},
        {"nome": "Consultora", "email": "tia@horizon.dev"},
        {"nome": "Outra", "email": "outra@consultoria.dev"},
        {"nome": "Alheio", "email": "alheio@outro-orgao.dev"},
        {"nome": "Proprio", "email": "proprio@prefeitura.dev"},
    ]
    previa = client.post(
        f"/projetos/{projeto_id}/importar/previa",
        headers=headers,
        files={"arquivo": ("f.csv", _csv(linhas), "text/csv")},
    ).json()
    erros = {linha["email"]: linha["erros"] for linha in previa["linhas"]}
    for email in (
        "joao@horizon.dev",
        "tia@horizon.dev",
        "outra@consultoria.dev",
        "alheio@outro-orgao.dev",
    ):
        assert any("use convite" in erro for erro in erros[email]), email
    assert erros["proprio@prefeitura.dev"] == []

    confirmadas = [
        {**linha, "cargo": "", "setor": "", "superior_email": "", "erros": []}
        for linha in linhas
    ]
    resposta = client.post(
        f"/projetos/{projeto_id}/importar/confirmar",
        headers=headers,
        json={"linhas": confirmadas},
    )
    assert resposta.status_code == 200
    assert resposta.json()["criados"] == 1
    vinculados = set(
        db.scalars(
            select(ProjetoUsuario.usuario_id).where(
                ProjetoUsuario.projeto_id == projeto_id,
                ProjetoUsuario.papel == "FUNCIONARIO",
            )
        ).all()
    )
    assert vinculados == {proprio}
    assert alheio not in vinculados
