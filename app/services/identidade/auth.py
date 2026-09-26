"""Login, sessão, primeiro acesso e recuperação de senha."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_senha, senha_confere
from app.core.tokens import (
    criar_access_token,
    criar_refresh_token,
    hash_token,
    novo_id,
    novo_token_opaco,
)
from app.models.convite import Convite
from app.models.sessao import Sessao
from app.models.token_redefinicao import TokenRedefinicao
from app.models.usuario import Usuario

from .convites import _link_com_token
from .erros import (
    MSG_CREDENCIAL,
    MSG_ESPERA,
    MSG_TOKEN,
    ErroAuth,
    _agora,
    _auditar,
    _ciente,
    _exigir_rate_publico,
    _exigir_senha,
    _hash_dummy,
    _usuario_por_email,
    email_acesso,
    limpar_falhas,
    painel_de,
    registrar_falha,
    segundos_bloqueio,
    settings,
)


def _emitir_sessao(db: Session, usuario: Usuario) -> dict[str, str]:
    sessao_id = novo_id()
    cru, token_hash, expira = criar_refresh_token(usuario.id)
    db.add(
        Sessao(
            id=sessao_id,
            usuario_id=usuario.id,
            token_hash=token_hash,
            expira_em=expira,
            revogado_em=None,
            criado_em=_agora(),
        )
    )
    access = criar_access_token(
        usuario.id, usuario.papel, sessao_id=sessao_id
    )
    return {
        "access_token": access,
        "refresh_token": cru,
        "token_type": "bearer",
        "painel": painel_de(usuario.papel),
    }


def garantir_admin(db: Session) -> None:
    """Cria a conta do TI a partir do .env, se ainda não existir.

    A senha do ambiente é analisada e só o hash vai para o banco.
    Não grava senha em log e não cria um segundo acesso de desenvolvimento.
    """
    nome = settings.admin_nome.strip()
    email = settings.admin_email.strip()
    senha = settings.admin_senha
    if not nome or not email or not senha:
        return
    _exigir_senha(senha)
    endereco = email_acesso(email)
    ja_ti = db.scalar(
        select(Usuario.id).where(
            Usuario.papel == "TI",
            Usuario.deleted_at.is_(None),
        )
    )
    if ja_ti is not None:
        return
    if _usuario_por_email(db, endereco) is not None:
        return
    agora = _agora()
    usuario = Usuario(
        nome=nome,
        email=endereco,
        senha_hash=hash_senha(senha),
        papel="TI",
        ativo=True,
        tentativas_falhas=0,
        criado_em=agora,
        atualizado_em=agora,
    )
    db.add(usuario)
    db.flush()
    _auditar(db, "ADMIN_CRIADO", usuario.id)
    db.commit()


def bootstrap(db: Session, nome: str, email: str, senha: str) -> dict[str, str]:
    """Só a primeira conta, e só se a tabela estiver vazia.

    Em produção a rota some (404): TI nasce via ADMIN_* / garantir_admin.
    """
    if settings.app_env == "production":
        raise ErroAuth(404, "Não encontrado.")
    existe = db.scalar(select(Usuario.id).limit(1))
    if existe is not None:
        raise ErroAuth(403, "Cadastro inicial já foi feito.")
    _exigir_senha(senha)
    endereco = email_acesso(email)
    usuario = Usuario(
        nome=nome.strip(),
        email=endereco,
        senha_hash=hash_senha(senha),
        papel="TI",
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


def refresh(
    db: Session,
    refresh_token: str,
    *,
    ip: str | None = None,
) -> dict[str, str]:
    """Três tokens inválidos no mesmo IP esperam 5 minutos. Sucesso zera."""
    chave = f"refresh:ip:{ip or 'sem-ip'}"
    _exigir_rate_publico(db, chave)
    sessao = db.scalar(
        select(Sessao).where(Sessao.token_hash == hash_token(refresh_token))
    )
    invalida = (
        sessao is None
        or sessao.revogado_em is not None
        or (_ciente(sessao.expira_em) or _agora()) <= _agora()
    )
    if not invalida:
        usuario = db.get(Usuario, sessao.usuario_id)
        if usuario is None or usuario.deleted_at is not None or not usuario.ativo:
            invalida = True
    if invalida:
        registrar_falha(db, chave)
        db.commit()
        raise ErroAuth(401, "Sessão inválida.")
    sessao.revogado_em = _agora()
    tokens = _emitir_sessao(db, usuario)
    limpar_falhas(db, chave)
    db.commit()
    return tokens


def sair(db: Session, refresh_token: str) -> None:
    sessao = db.scalar(
        select(Sessao).where(Sessao.token_hash == hash_token(refresh_token))
    )
    if sessao is not None and sessao.revogado_em is None:
        sessao.revogado_em = _agora()
        db.commit()


def primeiro_acesso(
    db: Session,
    token: str,
    senha: str,
    *,
    ip: str | None = None,
) -> dict[str, str]:
    chave_token = f"primeiro-acesso:tok:{hash_token(token)[:24]}"
    chave_ip = f"primeiro-acesso:ip:{ip}" if ip else ""
    _exigir_rate_publico(db, chave_token, chave_ip)
    try:
        _exigir_senha(senha)
    except ErroAuth:
        registrar_falha(db, chave_token)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
        raise
    convite = db.scalar(
        select(Convite).where(Convite.token_hash == hash_token(token))
    )
    if (
        convite is None
        or convite.status != "PENDENTE"
        or (_ciente(convite.expira_em) or _agora()) <= _agora()
    ):
        registrar_falha(db, chave_token)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
        raise ErroAuth(400, MSG_TOKEN)
    existente = _usuario_por_email(db, convite.email)
    if existente is not None and existente.senha_hash:
        registrar_falha(db, chave_token)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
        raise ErroAuth(409, "Este e-mail já tem acesso.")
    if existente is None:
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
    else:
        usuario = existente
        usuario.senha_hash = hash_senha(senha)
        usuario.ativo = True
        usuario.atualizado_em = _agora()
    convite.status = "ACEITO"
    convite.aceito_em = _agora()
    convite.atualizado_em = _agora()
    from app.services.projeto import vincular_aceite

    vincular_aceite(db, convite, usuario)
    limpar_falhas(db, chave_token)
    if chave_ip:
        limpar_falhas(db, chave_ip)
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
    from app.services.notificacao import entrega_aceita, entregar_email

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
    if not entrega_aceita(entrega):
        _auditar(db, "RECUPERACAO_FALHA_ENTREGA", usuario.id)
        db.commit()
        return
    _auditar(db, "RECUPERACAO_SOLICITADA", usuario.id)
    registrar_falha(db, chave)
    db.commit()


def redefinir_senha(
    db: Session,
    token: str,
    senha: str,
    *,
    ip: str | None = None,
) -> None:
    chave_token = f"redefinir:tok:{hash_token(token)[:24]}"
    chave_ip = f"redefinir:ip:{ip}" if ip else ""
    _exigir_rate_publico(db, chave_token, chave_ip)
    try:
        _exigir_senha(senha)
    except ErroAuth:
        registrar_falha(db, chave_token)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
        raise
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
        registrar_falha(db, chave_token)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
        raise ErroAuth(400, MSG_TOKEN)
    usuario = db.get(Usuario, linha.usuario_id)
    if usuario is None or usuario.deleted_at is not None or not usuario.ativo:
        registrar_falha(db, chave_token)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
        raise ErroAuth(400, MSG_TOKEN)
    usuario.senha_hash = hash_senha(senha)
    usuario.tentativas_falhas = 0
    usuario.bloqueado_ate = None
    usuario.atualizado_em = _agora()
    linha.usado_em = _agora()
    limpar_falhas(db, f"login:{usuario.email}")
    limpar_falhas(db, chave_token)
    if chave_ip:
        limpar_falhas(db, chave_ip)
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
