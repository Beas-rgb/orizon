"""O hash da senha não segura uma conexão do banco."""

from sqlalchemy import event

from app.core.security import senha_confere
from tests.contas import SENHA, abrir_dev


def test_login_solta_a_conexao_durante_o_hash(client, monkeypatch, db) -> None:
    abrir_dev(client, email="solta@horizon.dev")
    em_uso = {"n": 0}
    engine = db.get_bind()

    def checkout(*_args) -> None:
        em_uso["n"] += 1

    def checkin(*_args) -> None:
        em_uso["n"] -= 1

    event.listen(engine, "checkout", checkout)
    event.listen(engine, "checkin", checkin)
    visto: dict[str, int] = {}

    def espiao(senha: str, senha_hash: str) -> bool:
        visto["em_uso"] = em_uso["n"]
        return senha_confere(senha, senha_hash)

    monkeypatch.setattr("app.services.identidade.auth.senha_confere", espiao)
    try:
        resposta = client.post(
            "/auth/login",
            json={"email": "solta@horizon.dev", "senha": SENHA},
        )
    finally:
        event.remove(engine, "checkout", checkout)
        event.remove(engine, "checkin", checkin)
    assert resposta.status_code == 200
    assert visto["em_uso"] == 0
