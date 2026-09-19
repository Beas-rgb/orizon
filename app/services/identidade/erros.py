"""Erros, mensagens e utilitários compartilhados de identidade."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_senha, senha_aceita
from app.models.controle_acesso import ControleAcesso
from app.models.usuario import Usuario
from app.services.auditoria import registrar as _auditar

PAPEIS = {"CONSULTOR", "ORGAO", "FUNCIONARIO", "TI"}
MSG_CREDENCIAL = "E-mail ou senha inválidos."
MSG_ESPERA = "Muitas tentativas. Aguarde 5 minutos para tentar de novo."
MSG_RECUPERAR = (
    "Se o e-mail estiver cadastrado, enviaremos as instruções "
    "para o e-mail de acesso."
)
MSG_TOKEN = "Token inválido ou expirado."


class ErroAuth(Exception):
    def __init__(self, status: int, detalhe: str) -> None:
        self.status = status
        self.detalhe = detalhe


def _agora() -> datetime:
    return datetime.now(UTC)


def _ciente(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor


def email_acesso(valor: str) -> str:
    return valor.strip().lower()


def _hash_dummy() -> str:
    # Mesmo custo do Argon2 quando o e-mail não existe, para não vazar
    # existência da conta pelo tempo de resposta.
    if not hasattr(_hash_dummy, "valor"):
        _hash_dummy.valor = hash_senha("dummy-nao-e-conta")  # type: ignore[attr-defined]
    return _hash_dummy.valor  # type: ignore[attr-defined]


def segundos_bloqueio(db: Session, chave: str) -> int:
    linha = db.get(ControleAcesso, chave)
    if linha is None or linha.bloqueado_ate is None:
        return 0
    bloqueado = _ciente(linha.bloqueado_ate)
    if bloqueado is None:
        return 0
    restante = (bloqueado - _agora()).total_seconds()
    if restante <= 0:
        return 0
    return int(restante)


def registrar_falha(db: Session, chave: str) -> bool:
    """Soma 1. Na terceira, grava espera de 5 minutos. Devolve True se bloqueou."""
    agora = _agora()
    linha = db.get(ControleAcesso, chave)
    if linha is None:
        linha = ControleAcesso(
            chave=chave,
            tentativas=0,
            bloqueado_ate=None,
            atualizado_em=agora,
        )
        db.add(linha)
    bloqueado = _ciente(linha.bloqueado_ate)
    if bloqueado and bloqueado > agora:
        return True
    linha.tentativas += 1
    linha.atualizado_em = agora
    if linha.tentativas >= settings.login_max_tentativas:
        linha.bloqueado_ate = agora + timedelta(
            minutes=settings.login_espera_minutos
        )
        linha.tentativas = settings.login_max_tentativas
        return True
    return False


def limpar_falhas(db: Session, chave: str) -> None:
    linha = db.get(ControleAcesso, chave)
    if linha is None:
        return
    linha.tentativas = 0
    linha.bloqueado_ate = None
    linha.atualizado_em = _agora()


def _exigir_senha(senha: str) -> None:
    motivo = senha_aceita(senha)
    if motivo:
        raise ErroAuth(422, motivo)


PAINEIS = {
    "CONSULTOR": "consultora",
    "TI": "dev",
    "ORGAO": "orgao",
    "FUNCIONARIO": "funcionario",
}


def painel_de(papel: str) -> str:
    return PAINEIS.get(papel, "consultora")


def _exigir_rate_publico(db: Session, *chaves: str) -> None:
    """Bloqueia se qualquer chave estiver em espera (mesmo padrão do login)."""
    for chave in chaves:
        if not chave:
            continue
        if segundos_bloqueio(db, chave) > 0:
            db.commit()
            raise ErroAuth(429, MSG_ESPERA)


def _usuario_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(
        select(Usuario).where(
            Usuario.email == email,
            Usuario.deleted_at.is_(None),
        )
    )


def _usuario_soft_por_email(db: Session, email: str) -> Usuario | None:
    """Conta apagada logicamente. O e-mail ainda ocupa o unique no banco."""
    return db.scalar(
        select(Usuario).where(
            Usuario.email == email,
            Usuario.deleted_at.is_not(None),
        )
    )


__all__ = [
    "PAPEIS",
    "PAINEIS",
    "MSG_CREDENCIAL",
    "MSG_ESPERA",
    "MSG_RECUPERAR",
    "MSG_TOKEN",
    "ErroAuth",
    "_agora",
    "_auditar",
    "_ciente",
    "_exigir_rate_publico",
    "_exigir_senha",
    "_hash_dummy",
    "_usuario_por_email",
    "_usuario_soft_por_email",
    "email_acesso",
    "limpar_falhas",
    "painel_de",
    "registrar_falha",
    "segundos_bloqueio",
    "settings",
]
