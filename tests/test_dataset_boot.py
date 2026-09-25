"""Dataset de boot: 32 funcionários via importação (prova do script de staging)."""

from sqlalchemy import func, select

from app.integrations.cnpj import DadosCnpj
from app.models.estrutura import PerfilFuncionario
from app.models.usuario import Usuario
from scripts.contas_staging import TOTAL_FUNCIONARIOS, csv_dataset
from tests.contas import abrir_consultora


def _cnpj_falso(_cnpj: str) -> DadosCnpj:
    return DadosCnpj(
        cnpj="19131243000197",
        razao_social="Prefeitura Exemplo",
        nome_fantasia="Prefeitura",
        municipio="Brasilia",
        uf="DF",
    )


def test_dataset_32_contas_via_importacao(client, monkeypatch, db) -> None:
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
            "email_orgao": "rh-dataset@prefeitura.dev",
            "vinculo_tipo": "EDITAL",
            "vinculo_titulo": "Dataset boot",
        },
    ).json()
    projeto_id = projeto["id"]
    conteudo = csv_dataset(TOTAL_FUNCIONARIOS)
    previa = client.post(
        f"/projetos/{projeto_id}/importar/previa",
        headers=headers,
        files={"arquivo": ("dataset.csv", conteudo, "text/csv")},
    )
    assert previa.status_code == 200
    assert previa.json()["validos"] == TOTAL_FUNCIONARIOS
    confirmar = client.post(
        f"/projetos/{projeto_id}/importar/confirmar",
        headers=headers,
        json={"linhas": previa.json()["linhas"]},
    )
    assert confirmar.status_code == 200
    assert confirmar.json()["criados"] == TOTAL_FUNCIONARIOS
    funcs = db.scalar(
        select(func.count()).select_from(Usuario).where(Usuario.papel == "FUNCIONARIO")
    )
    assert funcs == TOTAL_FUNCIONARIOS
    perfis = db.scalar(select(func.count()).select_from(PerfilFuncionario))
    assert perfis == TOTAL_FUNCIONARIOS
    arvore = client.get(f"/projetos/{projeto_id}/arvore", headers=headers).json()
    assert len(arvore) == 1
    assert arvore[0]["email"] == "presidente.teste@staging.orizon.local"
