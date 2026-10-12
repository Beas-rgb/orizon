"""Convite em dois modos e sessão temporária 'testar como órgão'."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_senha
from app.core.tokens import novo_id
from app.models.base import agora
from app.models.projeto import ProjetoUsuario
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth, criar_convite
from app.services.identidade.auth import _emitir_sessao, _revogar_sessoes
from app.services.lab.cenario import obter_cenario
from app.services.lab.geradores import DOMINIO


def email_orgao_sintetico(cenario_id: str) -> str:
    return f"orgao.{cenario_id[:8]}@{DOMINIO}"


def garantir_orgao_sintetico(
    db: Session, cenario_id: str, projeto_id: str
) -> Usuario:
    email = email_orgao_sintetico(cenario_id)
    pessoa = db.scalar(select(Usuario).where(Usuario.email == email))
    if pessoa is None:
        agora_ = agora()
        pessoa = Usuario(
            id=novo_id(),
            nome="Órgão sintético",
            email=email,
            senha_hash=hash_senha(novo_id()),
            papel="ORGAO",
            tipo_conta="SINTETICO",
            ativo=True,
            tentativas_falhas=0,
            criado_em=agora_,
            atualizado_em=agora_,
        )
        db.add(pessoa)
        db.flush()
    vinculo = db.scalar(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.usuario_id == pessoa.id,
        )
    )
    if vinculo is None:
        db.add(
            ProjetoUsuario(
                id=novo_id(),
                projeto_id=projeto_id,
                usuario_id=pessoa.id,
                papel="ORGAO",
            )
        )
        db.flush()
    return pessoa


def entrar_como_orgao(db: Session, dono: Usuario, cenario_id: str) -> dict:
    """Sessão curta do órgão sintético. Nunca assume conta NORMAL."""
    cenario = obter_cenario(db, dono, cenario_id)
    if not cenario.projeto_id:
        raise ErroAuth(409, "Cenário ainda sem trabalho.")
    orgao = garantir_orgao_sintetico(db, cenario.id, cenario.projeto_id)
    if orgao.tipo_conta != "SINTETICO" or orgao.papel != "ORGAO":
        raise ErroAuth(409, "Órgão do cenário inválido.")
    _revogar_sessoes(db, orgao.id)
    from app.services.auditoria import registrar

    registrar(db, "LAB_TESTAR_COMO_ORGAO", dono.id)
    tokens = _emitir_sessao(db, orgao)
    db.commit()
    return tokens


def convidar_no_cenario(
    db: Session,
    dono: Usuario,
    cenario_id: str,
    nome: str,
    email: str,
    papel: str,
    modo: str,
    autorizo_envio: bool,
) -> dict:
    """SIMULADO não envia e-mail. REAL exige consentimento e fora de produção."""
    cenario = obter_cenario(db, dono, cenario_id)
    if not cenario.projeto_id:
        raise ErroAuth(409, "Cenário ainda sem trabalho.")
    modo = modo.strip().upper()
    if modo not in {"SIMULADO", "REAL"}:
        raise ErroAuth(422, "Modo de convite inválido.")
    if modo == "REAL":
        if settings.app_env == "production":
            raise ErroAuth(422, "Convite real não roda em produção.")
        if not autorizo_envio:
            raise ErroAuth(422, "Marque o consentimento para envio real.")
        saida = criar_convite(
            db, dono, nome, email, papel, cenario.projeto_id, enviar_email=True
        )
        return {"modo": "REAL", "enviado": True, **saida}
    destino = email.strip().lower()
    if not destino.endswith(f"@{DOMINIO}"):
        destino = f"convite.{cenario.id[:8]}@{DOMINIO}"
    saida = criar_convite(
        db,
        dono,
        nome,
        destino,
        papel,
        cenario.projeto_id,
        enviar_email=False,
    )
    return {"modo": "SIMULADO", "enviado": False, **saida}
