"""Respostas sintéticas via o serviço real."""

from sqlalchemy import func, select

from app.core.config import settings
from app.integrations.email import caixa_email
from app.main import incluir_lab_se_ligado
from app.models.pesquisa import Pesquisa, PesquisaParticipante, Resposta
from scripts.criar_consultor_teste import criar_consultor_teste
from tests.contas import SENHA


def _headers(client, email: str) -> dict[str, str]:
    entrada = client.post(
        "/auth/login",
        json={"email": email, "senha": SENHA},
    )
    assert entrada.status_code == 200
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_respostas_sinteticas_pelo_caminho_real(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-resp@horizon.dev", SENHA)
    headers = _headers(client, "lab-resp@horizon.dev")
    criado = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Resp",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 11,
            "perfil": "POSITIVO",
        },
    )
    assert criado.status_code == 202
    cid = criado.json()["id"]
    assert client.get(f"/lab/cenarios/{cid}", headers=headers).json()["status"] == (
        "PRONTO"
    )
    antes = len(caixa_email.mensagens)
    gerado = client.post(
        f"/lab/cenarios/{cid}/respostas",
        headers=headers,
        json={"perfil": "POSITIVO", "taxa": 1.0, "seed": 11},
    )
    assert gerado.status_code == 202, gerado.text
    final = client.get(f"/lab/cenarios/{cid}", headers=headers).json()
    assert final["status"] == "PRONTO", final
    assert len(caixa_email.mensagens) == antes

    pesquisa = db.scalar(
        select(Pesquisa).where(Pesquisa.projeto_id == final["projeto_id"])
    )
    assert pesquisa is not None
    respondidas = db.scalar(
        select(func.count())
        .select_from(PesquisaParticipante)
        .where(
            PesquisaParticipante.pesquisa_id == pesquisa.id,
            PesquisaParticipante.status == "RESPONDIDA",
        )
    )
    assert respondidas == 100
    total_resp = db.scalar(select(func.count()).select_from(Resposta))
    assert total_resp and total_resp >= 100
