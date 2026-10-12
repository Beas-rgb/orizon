"""Jobs de importação, convite e exportação. A resposta volta antes do lote."""

from app.models.usuario import Usuario
from tests.test_importacao import _projeto


def test_importacao_em_tarefa(client, monkeypatch, db) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    criado = client.post(
        f"/projetos/{projeto_id}/importar/tarefa",
        headers=headers,
        json={
            "linhas": [
                {
                    "nome": "Ana Job",
                    "email": "ana-job@prefeitura.dev",
                    "cargo": "Analista",
                    "setor": "RH",
                    "superior_email": "",
                    "erros": [],
                }
            ]
        },
    )
    assert criado.status_code == 202, criado.text
    tarefa_id = criado.json()["id"]
    detalhe = client.get(f"/tarefas/{tarefa_id}", headers=headers)
    assert detalhe.status_code == 200
    assert detalhe.json()["status"] == "CONCLUIDA"
    assert (
        db.query(Usuario).filter(Usuario.email == "ana-job@prefeitura.dev").count()
        == 1
    )


def test_exportacao_devolve_csv_so_ao_dono(client, monkeypatch) -> None:
    headers, projeto_id = _projeto(client, monkeypatch)
    criado = client.post(
        f"/projetos/{projeto_id}/exportar/tarefa",
        headers=headers,
    )
    assert criado.status_code == 202, criado.text
    tarefa_id = criado.json()["id"]
    arquivo = client.get(f"/tarefas/{tarefa_id}/arquivo", headers=headers)
    assert arquivo.status_code == 200
    assert "email" in arquivo.text
    assert client.get(f"/tarefas/{tarefa_id}/arquivo").status_code == 401
