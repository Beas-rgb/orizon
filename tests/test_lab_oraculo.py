"""Oráculo independente do motor de resultados."""

from sqlalchemy import select

from app.core.config import settings
from app.main import incluir_lab_se_ligado
from app.models.pesquisa import Pergunta, Pesquisa, Resposta
from app.services.lab.oraculo import (
    conferir_nota5,
    deve_suprimir,
    media_ponderada_desempenho,
)
from app.services.pesquisa.comum import K_ANONIMATO
from app.services.pesquisa.painel import painel
from scripts.criar_consultor_teste import criar_consultor_teste
from tests.contas import SENHA


def _headers(client, email: str) -> dict[str, str]:
    entrada = client.post(
        "/auth/login",
        json={"email": email, "senha": SENHA},
    )
    assert entrada.status_code == 200
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_k_anonimato_limite() -> None:
    assert deve_suprimir(4) is True
    assert deve_suprimir(5) is False
    assert K_ANONIMATO == 5


def test_media_ponderada_desempenho_a_mao() -> None:
    # AUTO=4 peso 1, SUPERIOR=5 peso 2, SUBORDINADO=3 peso 1 → (4+10+3)/4 = 4.25
    assert (
        abs(
            media_ponderada_desempenho(
                {"AUTO": 4.0, "SUPERIOR": 5.0, "SUBORDINADO": 3.0}
            )
            - 4.25
        )
        < 1e-9
    )


def test_oraculo_bate_com_painel_nota5(client, db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "enable_lab", True)
    incluir_lab_se_ligado()
    criar_consultor_teste(db, "Lab", "lab-ora@horizon.dev", SENHA)
    headers = _headers(client, "lab-ora@horizon.dev")
    cid = client.post(
        "/lab/cenarios",
        headers=headers,
        json={
            "nome": "Ora",
            "tipo": "CLIMA",
            "tamanho": 100,
            "seed": 21,
            "perfil": "NEUTRO",
        },
    ).json()["id"]
    client.post(
        f"/lab/cenarios/{cid}/respostas",
        headers=headers,
        json={"perfil": "NEUTRO", "taxa": 1.0, "seed": 21},
    )
    from app.models.lab import CenarioLab
    from app.models.usuario import Usuario

    cenario = db.get(CenarioLab, cid)
    assert cenario and cenario.projeto_id
    dono = db.scalar(
        select(Usuario).where(Usuario.email == "lab-ora@horizon.dev")
    )
    pesquisa = db.scalar(
        select(Pesquisa).where(Pesquisa.projeto_id == cenario.projeto_id)
    )
    assert pesquisa and dono
    painel_itens = painel(db, dono, pesquisa.id)
    nota5 = next(item for item in painel_itens if item["tipo"] == "NOTA_5")
    pergunta = db.get(Pergunta, nota5["pergunta_id"])
    assert pergunta is not None
    valores = [
        float(v)
        for v in db.scalars(
            select(Resposta.valor_numerico).where(
                Resposta.pergunta_id == pergunta.id,
                Resposta.valor_numerico.is_not(None),
            )
        ).all()
    ]
    # NEUTRO → todos 3; K satisfeito com 100 respondentes
    assert all(v == 3.0 for v in valores)
    conferir_nota5(nota5, valores)

    # K: com 4 respondentes distintos o painel omite
    conferir_nota5(
        {
            "suprimido": True,
            "media": None,
            "respostas": 4,
        },
        [3.0, 3.0, 3.0, 3.0],
    )
    conferir_nota5(
        {
            "suprimido": False,
            "media": 3.0,
            "respostas": 5,
        },
        [3.0, 3.0, 3.0, 3.0, 3.0],
    )
