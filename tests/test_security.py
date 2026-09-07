import pytest

from app.core.security import hash_senha, senha_confere


def test_hash_nao_e_a_senha() -> None:
    senha = "um-exemplo-so-de-teste"
    senha_hash = hash_senha(senha)
    assert senha_hash != senha
    assert senha not in senha_hash


def test_senha_certa_confere() -> None:
    senha_hash = hash_senha("senha-da-consultora")
    assert senha_confere("senha-da-consultora", senha_hash) is True


def test_senha_errada_nao_confere() -> None:
    senha_hash = hash_senha("senha-da-consultora")
    assert senha_confere("outra-senha", senha_hash) is False


def test_dois_hashes_da_mesma_senha_diferem() -> None:
    # O salt muda a cada hash. Por isso não se compara hash com hash.
    assert hash_senha("a-mesma") != hash_senha("a-mesma")


def test_senha_vazia_nao_gera_hash() -> None:
    with pytest.raises(ValueError):
        hash_senha("   ")


def test_hash_vazio_nao_confere() -> None:
    assert senha_confere("qualquer", "") is False
