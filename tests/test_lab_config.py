"""Configuração e conta do consultor de teste."""

import pytest

from app.schemas.auth import BootstrapEntrada, ConviteEntrada, LoginEntrada
from app.schemas.lab import CenarioCriar
from scripts.criar_consultor_teste import criar_consultor_teste


def test_criar_consultor_teste_via_script(db) -> None:
    pessoa = criar_consultor_teste(
        db,
        "Lab",
        "lab@horizon.dev",
        "Senha-segura1",
    )
    assert pessoa.papel == "CONSULTOR"
    assert pessoa.tipo_conta == "TESTE"
    assert pessoa.senha_hash is not None


def test_schemas_entrada_nao_aceitam_tipo_conta() -> None:
    """Nenhum schema de entrada define tipo_conta — o cliente não consegue gravar."""
    for cls in (LoginEntrada, BootstrapEntrada, ConviteEntrada, CenarioCriar):
        assert "tipo_conta" not in cls.model_fields

    login = LoginEntrada.model_validate(
        {"email": "a@b.com", "senha": "Senha-segura1", "tipo_conta": "TI"}
    )
    assert not hasattr(login, "tipo_conta")


def test_enable_lab_bloqueado_em_producao(monkeypatch) -> None:
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "app_env", "production")
    monkeypatch.setattr(cfg.settings, "jwt_secret", "x" * 32)
    monkeypatch.setattr(cfg.settings, "database_url", "sqlite://")
    monkeypatch.setattr(cfg.settings, "enable_lab", True)
    with pytest.raises(RuntimeError, match="ENABLE_LAB"):
        cfg.conferir_producao()
