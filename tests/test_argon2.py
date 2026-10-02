"""O hash antigo do passlib continua válido. Rehash só com senha certa."""

from sqlalchemy import select

from app.core.config import settings
from app.core.security import precisa_rehash, senha_confere
from app.models.usuario import Usuario
from tests.contas import SENHA, abrir_dev

# Gerado com passlib CryptContext(argon2) antes da troca: m=65536, t=3, p=4.
HASH_PASSLIB = (
    "$argon2id$v=19$m=65536,t=3,p=4$9T7HWIuxNoZQqlWq1Zozhg$"
    "gzFXzckM/7vbb/w0AnX9HgQ4xvpGwCkK+iDUnhk3lhM"
)


def test_hash_antigo_do_passlib_confere() -> None:
    assert senha_confere(SENHA, HASH_PASSLIB) is True
    assert senha_confere("outra-senha", HASH_PASSLIB) is False


def test_login_regrava_hash_quando_os_parametros_mudam(client, monkeypatch, db) -> None:
    abrir_dev(client, email="rehash@horizon.dev")
    pessoa = db.scalar(select(Usuario).where(Usuario.email == "rehash@horizon.dev"))
    pessoa.senha_hash = HASH_PASSLIB
    db.commit()
    antigo = pessoa.senha_hash

    monkeypatch.setattr(settings, "argon2_time_cost", 4)
    resposta = client.post(
        "/auth/login",
        json={"email": "rehash@horizon.dev", "senha": SENHA},
    )
    assert resposta.status_code == 200
    db.refresh(pessoa)
    assert pessoa.senha_hash != antigo
    assert senha_confere(SENHA, pessoa.senha_hash) is True
    assert precisa_rehash(pessoa.senha_hash) is False


def test_senha_errada_nao_regrava_hash(client, monkeypatch, db) -> None:
    abrir_dev(client, email="sem-rehash@horizon.dev")
    pessoa = db.scalar(
        select(Usuario).where(Usuario.email == "sem-rehash@horizon.dev")
    )
    pessoa.senha_hash = HASH_PASSLIB
    db.commit()

    monkeypatch.setattr(settings, "argon2_time_cost", 4)
    resposta = client.post(
        "/auth/login",
        json={"email": "sem-rehash@horizon.dev", "senha": "Errada-1!"},
    )
    assert resposta.status_code == 401
    db.refresh(pessoa)
    assert pessoa.senha_hash == HASH_PASSLIB
