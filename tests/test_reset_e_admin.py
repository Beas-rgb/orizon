"""Reset destrutivo travado e TI só pela via administrativa."""

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.main import preparar_banco
from app.models.usuario import Usuario
from scripts import reset_manter_ti as reset
from tests.contas import abrir_consultora

LOCAL = "postgresql+psycopg://u:p@127.0.0.1:5432/horizon"
CONFIRMA = reset.CONFIRMACAO


@pytest.mark.parametrize(
    ("url", "ambiente", "confirmacao", "extra", "motivo"),
    [
        (LOCAL, "production", CONFIRMA, "", "production"),
        (LOCAL, "development", "", "", "HORIZON_RESET_CONFIRMA"),
        (LOCAL, "development", "sim", "", "HORIZON_RESET_CONFIRMA"),
        ("", "development", CONFIRMA, "", "vazia"),
        (
            "postgresql+psycopg://u:p@ep-x-pooler.sa-east-1.aws.neon.tech/neondb",
            "development",
            CONFIRMA,
            "",
            "host fora",
        ),
        (
            "postgresql+psycopg://u:p@db.interno:5432/horizon",
            "staging",
            CONFIRMA,
            "outro.host",
            "host fora",
        ),
    ],
)
def test_reset_recusa(url, ambiente, confirmacao, extra, motivo) -> None:
    with pytest.raises(reset.ResetRecusado, match=motivo):
        reset.validar_alvo(url, ambiente, confirmacao, extra)


def test_reset_aceita_local_confirmado() -> None:
    reset.validar_alvo(LOCAL, "development", CONFIRMA)
    reset.validar_alvo("sqlite:///x.db", "development", CONFIRMA)
    reset.validar_alvo(
        "postgresql+psycopg://u:p@db.interno:5432/h", "staging", CONFIRMA, "db.interno"
    )


def test_reset_main_recusa_sem_abrir_conexao(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(
        reset, "get_engine", lambda: pytest.fail("não deveria conectar")
    )
    with pytest.raises(SystemExit, match="reset recusado"):
        reset.main()


def _ti_vivos(db) -> list[Usuario]:
    return list(
        db.scalars(
            select(Usuario).where(Usuario.papel == "TI", Usuario.deleted_at.is_(None))
        )
    )


def test_boot_cria_ti_do_ambiente_uma_vez(db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_nome", "TI Horizon")
    monkeypatch.setattr(settings, "admin_email", "ti@horizon.dev")
    monkeypatch.setattr(settings, "admin_senha", "Senha-segura1!")
    assert preparar_banco() == []
    assert preparar_banco() == []
    db.expire_all()
    vivos = _ti_vivos(db)
    assert [item.email for item in vivos] == ["ti@horizon.dev"]
    assert vivos[0].senha_hash and "Senha-segura1!" not in vivos[0].senha_hash


def test_boot_sem_admin_nao_cria_ti(db, monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_nome", "")
    monkeypatch.setattr(settings, "admin_email", "")
    monkeypatch.setattr(settings, "admin_senha", "")
    assert preparar_banco() == []
    assert _ti_vivos(db) == []


def test_convite_nunca_concede_ti_mesmo_sem_ti(client, db) -> None:
    headers = abrir_consultora(client)
    for pessoa in _ti_vivos(db):
        db.delete(pessoa)
    db.commit()
    assert _ti_vivos(db) == []
    resposta = client.post(
        "/auth/convites",
        headers=headers,
        json={"nome": "Dev", "email": "dev-novo@horizon.dev", "papel": "TI"},
    )
    assert resposta.status_code == 422
    assert _ti_vivos(db) == []
