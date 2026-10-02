"""Tokens curtos para carga em staging. Nunca logam o token."""

from __future__ import annotations

from datetime import timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tokens import ALGORITMO, hash_token, novo_id, novo_token_opaco
from app.models.base import agora
from app.models.pesquisa import Pesquisa
from app.models.sessao import Sessao
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth
from app.services.lab.cenario import obter_cenario

LIMITE_TOKENS = 5000
MINUTOS = 30


def emitir_tokens_carga(
    db: Session,
    dono: Usuario,
    cenario_id: str,
    quantidade: int,
) -> list[dict[str, str]]:
    if not settings.lab_tokens_permitidos:
        raise ErroAuth(404, "Não encontrado.")
    if quantidade < 1 or quantidade > LIMITE_TOKENS:
        raise ErroAuth(422, "Quantidade inválida.")
    cenario = obter_cenario(db, dono, cenario_id)
    if cenario.status != "PRONTO" or not cenario.projeto_id:
        raise ErroAuth(409, "Cenário ainda não está pronto.")
    pesquisa = db.scalar(
        select(Pesquisa).where(
            Pesquisa.projeto_id == cenario.projeto_id,
            Pesquisa.deleted_at.is_(None),
            Pesquisa.status == "PUBLICADA",
        )
    )
    if pesquisa is None:
        raise ErroAuth(404, "Pesquisa do cenário não encontrada.")
    sinteticos = list(
        db.scalars(
            select(Usuario)
            .where(
                Usuario.tipo_conta == "SINTETICO",
                Usuario.email.like(f"%.{cenario_id[:8]}@sintetico.invalid"),
                Usuario.deleted_at.is_(None),
            )
            .limit(quantidade)
        ).all()
    )
    if len(sinteticos) < quantidade:
        raise ErroAuth(422, "Não há sintéticos suficientes.")
    if not settings.jwt_secret:
        raise ErroAuth(500, "JWT ausente.")
    agora_ = agora()
    saida: list[dict[str, str]] = []
    for pessoa in sinteticos:
        sessao_id = novo_id()
        cru = novo_token_opaco()
        db.add(
            Sessao(
                id=sessao_id,
                usuario_id=pessoa.id,
                token_hash=hash_token(cru),
                expira_em=agora_ + timedelta(minutes=MINUTOS),
                revogado_em=None,
                criado_em=agora_,
            )
        )
        access = jwt.encode(
            {
                "sub": pessoa.id,
                "papel": pessoa.papel,
                "typ": "access",
                "sid": sessao_id,
                "exp": agora_ + timedelta(minutes=MINUTOS),
            },
            settings.jwt_secret,
            algorithm=ALGORITMO,
        )
        saida.append(
            {
                "usuario_id": pessoa.id,
                "token": access,
                "pesquisa_id": pesquisa.id,
            }
        )
    db.commit()
    return saida
