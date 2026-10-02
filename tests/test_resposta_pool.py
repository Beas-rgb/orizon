"""Esgotar o pool no meio do envio devolve 503 e não grava pela metade."""

from sqlalchemy import func, select
from sqlalchemy.exc import TimeoutError as PoolTimeout
from sqlalchemy.orm import Session as SessaoOrm

from app.models.pesquisa import PesquisaParticipante, Resposta
from tests.test_responder_auth import (
    _convidar_funcionario,
    _projeto_com_pesquisa,
)


def test_pool_estourado_na_resposta_nao_grava_parcial(
    client, db, monkeypatch
) -> None:
    headers, projeto_id, pid, token = _projeto_com_pesquisa(client, monkeypatch)
    acesso = _convidar_funcionario(
        client, headers, projeto_id, "pool-resp@prefeitura.dev"
    )
    pergunta_id = client.get(f"/responder/{token}", headers=acesso).json()[0]["id"]

    def commit_estoura(self) -> None:
        raise PoolTimeout("pool", "timeout", "timeout")

    monkeypatch.setattr(SessaoOrm, "commit", commit_estoura)
    resposta = client.post(
        f"/responder/{token}",
        headers=acesso,
        json={
            "respostas": [
                {"pergunta_id": pergunta_id, "valor_numerico": 4},
            ]
        },
    )
    assert resposta.status_code == 503
    assert resposta.status_code != 500
    assert resposta.headers["retry-after"] == "3"

    db.expire_all()
    participante = db.scalar(
        select(PesquisaParticipante).where(
            PesquisaParticipante.pesquisa_id == pid
        )
    )
    assert participante is not None
    assert participante.status != "RESPONDIDA"
    gravadas = db.scalar(
        select(func.count())
        .select_from(Resposta)
        .where(Resposta.pergunta_id == pergunta_id)
    )
    assert gravadas == 0
