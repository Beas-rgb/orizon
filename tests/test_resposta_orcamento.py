"""Uma pergunta cabe em 20 comandos e 1 commit."""

from sqlalchemy import event
from sqlalchemy.orm import Session as SessaoOrm

from tests.test_consulta_auth import contar
from tests.test_responder_auth import (
    _convidar_funcionario,
    _projeto_com_pesquisa,
)


def test_resposta_de_uma_pergunta_cabe_no_teto(client, db, monkeypatch) -> None:
    headers, projeto_id, _pid, token = _projeto_com_pesquisa(client, monkeypatch)
    func = _convidar_funcionario(
        client, headers, projeto_id, "servidor-orc@prefeitura.dev"
    )
    pergunta_id = client.get(f"/responder/{token}", headers=func).json()[0]["id"]
    commits = {"n": 0}

    def ouvir_commit(_sessao) -> None:
        commits["n"] += 1

    event.listen(SessaoOrm, "after_commit", ouvir_commit)
    try:
        resposta, total = contar(
            db.get_bind(),
            lambda: client.post(
                f"/responder/{token}",
                headers=func,
                json={
                    "respostas": [
                        {"pergunta_id": pergunta_id, "valor_numerico": 4},
                    ]
                },
            ),
        )
    finally:
        event.remove(SessaoOrm, "after_commit", ouvir_commit)
    assert resposta.status_code == 200, resposta.text
    assert total <= 20, total
    assert commits["n"] == 1
