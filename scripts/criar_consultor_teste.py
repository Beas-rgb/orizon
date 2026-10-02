"""Conta CONSULTOR de teste. Lê e-mail e senha do terminal, nunca de arquivo."""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, get_engine
from app.core.security import hash_senha, senha_aceita
from app.core.tokens import novo_id
from app.models.base import agora
from app.models.usuario import Usuario
from app.services.identidade.erros import email_acesso


def criar_consultor_teste(
    db,
    nome: str,
    email: str,
    senha: str,
) -> Usuario:
    """Cria ou atualiza a conta TESTE. Papel CONSULTOR — sem permissão de TI."""
    erro = senha_aceita(senha)
    if erro:
        raise ValueError(erro)
    endereco = email_acesso(email)
    existente = db.scalar(
        select(Usuario).where(
            Usuario.email == endereco,
            Usuario.deleted_at.is_(None),
        )
    )
    agora_ = agora()
    if existente is not None:
        if existente.papel != "CONSULTOR":
            raise ValueError("Este e-mail já existe com outro papel.")
        existente.tipo_conta = "TESTE"
        existente.senha_hash = hash_senha(senha)
        existente.ativo = True
        existente.nome = nome.strip()[:160]
        existente.atualizado_em = agora_
        db.commit()
        db.refresh(existente)
        return existente
    pessoa = Usuario(
        id=novo_id(),
        nome=nome.strip()[:160],
        email=endereco,
        senha_hash=hash_senha(senha),
        papel="CONSULTOR",
        tipo_conta="TESTE",
        ativo=True,
        tentativas_falhas=0,
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )
    db.add(pessoa)
    db.commit()
    db.refresh(pessoa)
    return pessoa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cria o consultor de teste do laboratório."
    )
    parser.add_argument(
        "--confirmo-producao",
        action="store_true",
        help="Obrigatório se APP_ENV=production.",
    )
    parser.add_argument("--nome", default="Consultor de Teste")
    args = parser.parse_args(argv)

    if settings.app_env == "production" and not args.confirmo_producao:
        print(
            "Recusado: APP_ENV=production sem --confirmo-producao.",
            file=sys.stderr,
        )
        return 2

    email = input("E-mail do consultor de teste: ").strip()
    senha = getpass.getpass("Senha: ")
    if not email or not senha:
        print("E-mail e senha são obrigatórios.", file=sys.stderr)
        return 2

    get_engine()
    if SessionLocal is None:
        print("DATABASE_URL ausente.", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        pessoa = criar_consultor_teste(db, args.nome, email, senha)
        print(f"ok tipo_conta={pessoa.tipo_conta} papel={pessoa.papel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
