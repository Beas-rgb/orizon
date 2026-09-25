"""Cenário ORIZON-TEST-500: 500 funcionários, hierarquia e importação."""

from sqlalchemy import func, select

from app.integrations.cnpj import DadosCnpj
from app.models.estrutura import PerfilFuncionario
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
            "vinculo_titulo": "ORIZON-TEST-500",
        },
    )
    return headers, projeto.json()["id"]


def test_cenario_500_funcionarios(client, monkeypatch, db) -> None:
    """500 funcionários, 10 setores, 20 cargos, 5 níveis. Sem erro."""
    headers, projeto_id = _projeto(client, monkeypatch)
    setores = []
    for i in range(10):
        setor = client.post(
            f"/projetos/{projeto_id}/setores",
            headers=headers,
            json={"nome": f"Setor {i}"},
        ).json()
        setores.append(setor)
    cargos = []
    for i in range(20):
        cargo = client.post(
            f"/projetos/{projeto_id}/cargos",
            headers=headers,
            json={"nome": f"Cargo {i}"},
        ).json()
        cargos.append(cargo)

    # 5 níveis: presidente → diretor → gerente → coordenador → funcionário
    niveis = ["presidente", "diretor", "gerente", "coordenador", "funcionario"]
    emails_por_nivel: dict[str, list[str]] = {n: [] for n in niveis}
    for nivel in niveis:
        quantidade = (
            1
            if nivel == "presidente"
            else 5
            if nivel == "diretor"
            else 25
            if nivel == "gerente"
            else 100
            if nivel == "coordenador"
            else 369
        )
        for i in range(quantidade):
            emails_por_nivel[nivel].append(f"{nivel}{i}@prefeitura.dev")

    linhas = []
    for nivel, emails in emails_por_nivel.items():
        for i, email in enumerate(emails):
            superior = ""
            if nivel != "presidente":
                nivel_superior = niveis[niveis.index(nivel) - 1]
                superior = emails_por_nivel[nivel_superior][
                    i % len(emails_por_nivel[nivel_superior])
                ]
            linhas.append(
                {
                    "nome": f"{nivel.title()} {i}",
                    "email": email,
                    "cargo": cargos[i % len(cargos)]["nome"],
                    "setor": setores[i % len(setores)]["nome"],
                    "superior_email": superior,
                    "erros": [],
                }
            )

    assert len(linhas) == 500
    resp = client.post(
        f"/projetos/{projeto_id}/importar/confirmar",
        headers=headers,
        json={"linhas": linhas},
    )
    assert resp.status_code == 200
    assert resp.json()["criados"] == 500

    usuarios = db.scalar(
        select(func.count()).select_from(Usuario).where(Usuario.papel == "FUNCIONARIO")
    )
    assert usuarios == 500
    perfis = db.scalar(
        select(func.count()).select_from(PerfilFuncionario).where(
            PerfilFuncionario.projeto_id == projeto_id
        )
    )
    assert perfis == 500

    arvore = client.get(f"/projetos/{projeto_id}/arvore", headers=headers).json()
    assert len(arvore) == 1  # presidente
    assert len(arvore[0]["subordinados"]) == 5  # diretores


def test_cenario_500_performance_aceitavel(client, monkeypatch, db) -> None:
    """A importação de 500 linhas não pode travar o banco."""
    import time

    headers, projeto_id = _projeto(client, monkeypatch)
    setor = client.post(
        f"/projetos/{projeto_id}/setores",
        headers=headers,
        json={"nome": "Geral"},
    ).json()
    cargo = client.post(
        f"/projetos/{projeto_id}/cargos",
        headers=headers,
        json={"nome": "Analista"},
    ).json()
    linhas = [
        {
            "nome": f"Func {i}",
            "email": f"func{i}@prefeitura.dev",
            "cargo": cargo["nome"],
            "setor": setor["nome"],
            "superior_email": "",
            "erros": [],
        }
        for i in range(500)
    ]
    t0 = time.perf_counter()
    resp = client.post(
        f"/projetos/{projeto_id}/importar/confirmar",
        headers=headers,
        json={"linhas": linhas},
    )
    duracao = time.perf_counter() - t0
    assert resp.status_code == 200
    assert resp.json()["criados"] == 500
    # SQLite em memória: deve ser rápido. Neon vai ser mais lento, mas
    # o limite aqui é só para pegar regressão grosseira.
    assert duracao < 30
