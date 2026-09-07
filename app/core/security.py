"""Senha com Argon2id.

A senha nunca fica no banco em texto puro. O que se guarda é um hash:
um texto irreversível gerado a partir da senha. Na entrada, o sistema
compara a senha digitada com o hash — não recupera a senha antiga.

Argon2id atrasa tentativa em massa (força bruta). Ainda assim, login
vai ter limite de tentativas na rota, quando ela existir.
"""

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Gera o hash. Nunca logar o valor de `senha` nem o retorno."""
    if not senha or not senha.strip():
        raise ValueError("senha vazia")
    return _pwd.hash(senha)


def senha_confere(senha: str, senha_hash: str) -> bool:
    """True só se a senha digitada corresponde ao hash guardado."""
    if not senha or not senha_hash:
        return False
    return _pwd.verify(senha, senha_hash)
