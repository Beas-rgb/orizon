"""Regras de identidade. A rota só chama daqui.

Ataques que este módulo corta:
- força bruta no login: 3 erros gravam bloqueio de 5 minutos no banco
- senha no e-mail: o convite e a recuperação levam só um token de uso único
- enumeração no recuperar: a resposta é a mesma se o e-mail existe ou não
- reuso de token: o hash é marcado como usado e as sessões antigas caem
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_senha, senha_confere
from app.core.tokens import (
    criar_access_token,
    criar_refresh_token,
    hash_token,
    novo_id,
    novo_token_opaco,
)
from app.models.auditoria import LogAuditoria
from app.models.controle_acesso import ControleAcesso
from app.models.convite import Convite
from app.models.projeto import Projeto
from app.models.sessao import Sessao
from app.models.token_redefinicao import TokenRedefinicao
from app.models.usuario import Usuario

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


def _auditar(db: Session, acao: str, usuario_id: str | None) -> None:
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=usuario_id,
            acao=acao,
            criado_em=_agora(),
        )
    )


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
    if len(senha) < 8 or senha.strip() != senha:
        raise ErroAuth(422, "A senha precisa ter ao menos 8 caracteres.")


PAINEIS = {
    "CONSULTOR": "consultora",
    "TI": "dev",
    "ORGAO": "orgao",
    "FUNCIONARIO": "funcionario",
}


def painel_de(papel: str) -> str:
    return PAINEIS.get(papel, "consultora")


def _link_com_token(pagina: str, token: str) -> str:
    base = settings.app_public_url.rstrip("/")
    if pagina == "primeiro-acesso.html":
        return f"{base}/#{token}"
    return f"{base}/{pagina}#{token}"


def _emitir_sessao(db: Session, usuario: Usuario) -> dict[str, str]:
    access = criar_access_token(usuario.id, usuario.papel)
    cru, token_hash, expira = criar_refresh_token(usuario.id)
    db.add(
        Sessao(
            id=novo_id(),
            usuario_id=usuario.id,
            token_hash=token_hash,
            expira_em=expira,
            revogado_em=None,
            criado_em=_agora(),
        )
    )
    return {
        "access_token": access,
        "refresh_token": cru,
        "token_type": "bearer",
        "painel": painel_de(usuario.papel),
    }


def _usuario_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(
        select(Usuario).where(
            Usuario.email == email,
            Usuario.deleted_at.is_(None),
        )
    )


def bootstrap(db: Session, nome: str, email: str, senha: str) -> dict[str, str]:
    """Só a primeira conta, e só se a tabela estiver vazia."""
    existe = db.scalar(select(Usuario.id).limit(1))
    if existe is not None:
        raise ErroAuth(403, "Cadastro inicial já foi feito.")
    _exigir_senha(senha)
    endereco = email_acesso(email)
    usuario = Usuario(
        nome=nome.strip(),
        email=endereco,
        senha_hash=hash_senha(senha),
        papel="CONSULTOR",
        ativo=True,
        tentativas_falhas=0,
    )
    db.add(usuario)
    db.flush()
    _auditar(db, "BOOTSTRAP", usuario.id)
    tokens = _emitir_sessao(db, usuario)
    db.commit()
    return tokens


def login(db: Session, email: str, senha: str) -> dict[str, str]:
    endereco = email_acesso(email)
    chave = f"login:{endereco}"
    if segundos_bloqueio(db, chave) > 0:
        _auditar(db, "LOGIN_BLOQUEADO", None)
        db.commit()
        raise ErroAuth(429, MSG_ESPERA)

    usuario = _usuario_por_email(db, endereco)
    hash_guardado = usuario.senha_hash if usuario and usuario.ativo else None
    confere = senha_confere(senha, hash_guardado or _hash_dummy())
    if usuario is None or not usuario.ativo or not hash_guardado or not confere:
        bloqueou = registrar_falha(db, chave)
        if usuario is not None:
            usuario.tentativas_falhas += 1
            usuario.atualizado_em = _agora()
            if bloqueou:
                usuario.bloqueado_ate = _agora() + timedelta(
                    minutes=settings.login_espera_minutos
                )
        _auditar(db, "LOGIN_FALHA", usuario.id if usuario else None)
        db.commit()
        if bloqueou:
            raise ErroAuth(429, MSG_ESPERA)
        raise ErroAuth(401, MSG_CREDENCIAL)

    limpar_falhas(db, chave)
    usuario.tentativas_falhas = 0
    usuario.bloqueado_ate = None
    usuario.atualizado_em = _agora()
    _auditar(db, "LOGIN", usuario.id)
    tokens = _emitir_sessao(db, usuario)
    db.commit()
    return tokens


def refresh(db: Session, refresh_token: str) -> dict[str, str]:
    sessao = db.scalar(
        select(Sessao).where(Sessao.token_hash == hash_token(refresh_token))
    )
    if (
        sessao is None
        or sessao.revogado_em is not None
        or (_ciente(sessao.expira_em) or _agora()) <= _agora()
    ):
        raise ErroAuth(401, "Sessão inválida.")
    usuario = db.get(Usuario, sessao.usuario_id)
    if usuario is None or usuario.deleted_at is not None or not usuario.ativo:
        raise ErroAuth(401, "Sessão inválida.")
    sessao.revogado_em = _agora()
    tokens = _emitir_sessao(db, usuario)
    db.commit()
    return tokens


def sair(db: Session, refresh_token: str) -> None:
    sessao = db.scalar(
        select(Sessao).where(Sessao.token_hash == hash_token(refresh_token))
    )
    if sessao is not None and sessao.revogado_em is None:
        sessao.revogado_em = _agora()
        db.commit()


def _vaga_de_acesso(
    db: Session,
    consultor: Usuario,
    papel: str,
    projeto_id: str | None,
) -> None:
    """Uma consultora, um dev e um órgão. Cada funcionário entra no projeto dela."""
    if papel == "CONSULTOR":
        raise ErroAuth(422, "Já existe a consultora. Não abre outra conta.")
    if papel == "FUNCIONARIO":
        if not projeto_id:
            raise ErroAuth(422, "O funcionário entra pelo projeto.")
        projeto = db.get(Projeto, projeto_id)
        if (
            projeto is None
            or projeto.deleted_at is not None
            or projeto.consultor_id != consultor.id
        ):
            raise ErroAuth(404, "Projeto não encontrado.")
        return
    if papel == "TI":
        ja = db.scalar(
            select(Usuario.id).where(
                Usuario.papel == "TI",
                Usuario.deleted_at.is_(None),
            )
        )
        pendente = db.scalar(
            select(Convite.id).where(
                Convite.papel == "TI",
                Convite.status == "PENDENTE",
            )
        )
        if ja is not None or pendente is not None:
            raise ErroAuth(409, "Já existe o acesso de desenvolvimento.")
        return
    if papel == "ORGAO":
        ja = db.scalar(
            select(Usuario.id).where(
                Usuario.papel == "ORGAO",
                Usuario.deleted_at.is_(None),
            )
        )
        pendente = db.scalar(
            select(Convite.id).where(
                Convite.papel == "ORGAO",
                Convite.status == "PENDENTE",
            )
        )
        if ja is not None or pendente is not None:
            raise ErroAuth(409, "Já existe o acesso do órgão.")


def criar_convite(
    db: Session,
    consultor: Usuario,
    nome: str,
    email: str,
    papel: str,
    projeto_id: str | None = None,
) -> None:
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(403, "Só a consultora convida.")
    chave = f"convite:{consultor.id}"
    if papel != "FUNCIONARIO" and segundos_bloqueio(db, chave) > 0:
        db.commit()
        raise ErroAuth(429, MSG_ESPERA)
    if papel not in PAPEIS:
        raise ErroAuth(422, "Papel inválido.")
    _vaga_de_acesso(db, consultor, papel, projeto_id)
    endereco = email_acesso(email)
    if _usuario_por_email(db, endereco) is not None:
        raise ErroAuth(409, "Este e-mail já tem acesso.")
    token = novo_token_opaco()
    convite = Convite(
        email=endereco,
        nome=nome.strip(),
        papel=papel,
        token_hash=hash_token(token),
        status="PENDENTE",
        entrega="NAO_ENVIADO",
        expira_em=_agora() + timedelta(hours=48),
        convidado_por_id=consultor.id,
        projeto_id=projeto_id,
    )
    db.add(convite)
    db.flush()
    from app.services.notificacao import entregar_email

    entrega = entregar_email(
        db,
        endereco,
        "Horizon — primeiro acesso",
        (
            "A consultora convidou você para o Horizon.\n"
            "Abra o link, defina sua senha. Ela não é enviada neste e-mail.\n"
            "Válido por 48 horas:\n\n"
            f"{_link_com_token('primeiro-acesso.html', token)}\n\n"
            f"{token}\n"
        ),
        "CONVITE",
        projeto_id,
        consultor.id,
    )
    convite.entrega = "ENVIADO" if entrega.status == "ENVIADO" else "FALHA"
    if papel != "FUNCIONARIO":
        registrar_falha(db, chave)
    convite.atualizado_em = _agora()
    _auditar(db, "CONVITE_CRIADO", consultor.id)
    db.commit()


def primeiro_acesso(db: Session, token: str, senha: str) -> dict[str, str]:
    _exigir_senha(senha)
    convite = db.scalar(
        select(Convite).where(Convite.token_hash == hash_token(token))
    )
    if (
        convite is None
        or convite.status != "PENDENTE"
        or (_ciente(convite.expira_em) or _agora()) <= _agora()
    ):
        raise ErroAuth(400, MSG_TOKEN)
    if _usuario_por_email(db, convite.email) is not None:
        raise ErroAuth(409, "Este e-mail já tem acesso.")
    usuario = Usuario(
        nome=convite.nome,
        email=convite.email,
        senha_hash=hash_senha(senha),
        papel=convite.papel,
        ativo=True,
        tentativas_falhas=0,
    )
    db.add(usuario)
    db.flush()
    convite.status = "ACEITO"
    convite.aceito_em = _agora()
    convite.atualizado_em = _agora()
    from app.services.projeto import vincular_aceite

    vincular_aceite(db, convite, usuario)
    _auditar(db, "PRIMEIRO_ACESSO", usuario.id)
    tokens = _emitir_sessao(db, usuario)
    db.commit()
    return tokens


def recuperar_senha(db: Session, email: str) -> None:
    """Sempre a mesma resposta. O token, se existir, vai ao e-mail de acesso."""
    endereco = email_acesso(email)
    chave = f"recuperar:{endereco}"
    if segundos_bloqueio(db, chave) > 0:
        db.commit()
        return
    usuario = _usuario_por_email(db, endereco)
    if usuario is None or not usuario.ativo or not usuario.senha_hash:
        registrar_falha(db, chave)
        db.commit()
        return
    _revogar_tokens_abertos(db, usuario.id)
    token = novo_token_opaco()
    db.add(
        TokenRedefinicao(
            id=novo_id(),
            usuario_id=usuario.id,
            token_hash=hash_token(token),
            expira_em=_agora() + timedelta(minutes=30),
            usado_em=None,
            criado_em=_agora(),
        )
    )
    from app.services.notificacao import entregar_email

    entrega = entregar_email(
        db,
        usuario.email,
        "Horizon — redefinir senha",
        (
            "Recebemos um pedido para redefinir a senha desta conta.\n"
            "Abra o link. A senha nova não é enviada.\n"
            "Válido por 30 minutos:\n\n"
            f"{_link_com_token('redefinir.html', token)}\n\n"
            f"{token}\n"
        ),
        "RECUPERACAO",
        None,
        usuario.id,
    )
    if entrega.status != "ENVIADO":
        _auditar(db, "RECUPERACAO_FALHA_ENTREGA", usuario.id)
        db.commit()
        return
    _auditar(db, "RECUPERACAO_SOLICITADA", usuario.id)
    registrar_falha(db, chave)
    db.commit()


def redefinir_senha(db: Session, token: str, senha: str) -> None:
    _exigir_senha(senha)
    linha = db.scalar(
        select(TokenRedefinicao).where(
            TokenRedefinicao.token_hash == hash_token(token)
        )
    )
    if (
        linha is None
        or linha.usado_em is not None
        or (_ciente(linha.expira_em) or _agora()) <= _agora()
    ):
        raise ErroAuth(400, MSG_TOKEN)
    usuario = db.get(Usuario, linha.usuario_id)
    if usuario is None or usuario.deleted_at is not None or not usuario.ativo:
        raise ErroAuth(400, MSG_TOKEN)
    usuario.senha_hash = hash_senha(senha)
    usuario.tentativas_falhas = 0
    usuario.bloqueado_ate = None
    usuario.atualizado_em = _agora()
    linha.usado_em = _agora()
    limpar_falhas(db, f"login:{usuario.email}")
    _revogar_sessoes(db, usuario.id)
    _auditar(db, "SENHA_REDEFINIDA", usuario.id)
    db.commit()


def _revogar_tokens_abertos(db: Session, usuario_id: str) -> None:
    abertos = db.scalars(
        select(TokenRedefinicao).where(
            TokenRedefinicao.usuario_id == usuario_id,
            TokenRedefinicao.usado_em.is_(None),
        )
    ).all()
    agora = _agora()
    for item in abertos:
        item.usado_em = agora


def _revogar_sessoes(db: Session, usuario_id: str) -> None:
    sessoes = db.scalars(
        select(Sessao).where(
            Sessao.usuario_id == usuario_id,
            Sessao.revogado_em.is_(None),
        )
    ).all()
    agora = _agora()
    for sessao in sessoes:
        sessao.revogado_em = agora
