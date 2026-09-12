"""Regras de identidade. A rota só chama daqui.

Ataques que este módulo corta:
- força bruta no login: 3 erros gravam bloqueio de 5 minutos no banco
- senha no e-mail: o convite e a recuperação levam só um token de uso único
- enumeração no recuperar: a resposta é a mesma se o e-mail existe ou não
- reuso de token: o hash é marcado como usado e as sessões antigas caem
"""

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings, url_publica
from app.core.security import hash_senha, senha_aceita, senha_confere
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
from app.models.pedido_consultora import PedidoConsultora
from app.models.pesquisa import Pesquisa
from app.models.projeto import Projeto, ProjetoUsuario
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


def _link_com_token(pagina: str, token: str) -> str:
    """Link do React em /app. Nunca aponta para HTML legado."""
    base = url_publica().rstrip("/")
    # pagina legado → rota React equivalente
    rotas = {
        "primeiro-acesso.html": "primeiro-acesso",
        "redefinir.html": "recuperar",
        "primeiro-acesso": "primeiro-acesso",
        "recuperar": "recuperar",
    }
    caminho = rotas.get(pagina, pagina.removesuffix(".html"))
    return f"{base}/{caminho}#{token}"


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
        # Ataque que corta: um órgão de outro cliente bloquear o onboarding
        # do próximo. A vaga é por projeto, não no sistema inteiro.
        if not projeto_id:
            raise ErroAuth(422, "O órgão entra pelo projeto.")
        projeto = db.get(Projeto, projeto_id)
        if (
            projeto is None
            or projeto.deleted_at is not None
            or projeto.consultor_id != consultor.id
        ):
            raise ErroAuth(404, "Projeto não encontrado.")
        ja = db.scalar(
            select(ProjetoUsuario.id).where(
                ProjetoUsuario.projeto_id == projeto_id,
                ProjetoUsuario.papel == "ORGAO",
            )
        )
        pendente = db.scalar(
            select(Convite.id).where(
                Convite.projeto_id == projeto_id,
                Convite.papel == "ORGAO",
                Convite.status == "PENDENTE",
            )
        )
        if ja is not None or pendente is not None:
            raise ErroAuth(409, "Já existe o acesso do órgão neste projeto.")
        return


def criar_convite(
    db: Session,
    consultor: Usuario,
    nome: str,
    email: str,
    papel: str,
    projeto_id: str | None = None,
) -> dict[str, str | None]:
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
    link = _link_com_token("primeiro-acesso.html", token)
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
            f"{link}\n\n"
            f"{token}\n"
        ),
        "CONVITE",
        projeto_id,
        consultor.id,
    )
    convite.entrega = "ENVIADO" if entrega.status == "ENVIADO" else "FALHA"
    # B6: o contador de espera é só para abuso / falha real de envio.
    # Somar em sucesso travava o 4º convite de órgão (429 falso).
    if papel != "FUNCIONARIO":
        if convite.entrega == "ENVIADO":
            limpar_falhas(db, chave)
        else:
            registrar_falha(db, chave)
    convite.atualizado_em = _agora()
    _auditar(db, "CONVITE_CRIADO", consultor.id)
    db.commit()
    from app.integrations.email import modo_envio

    saida: dict[str, str | None] = {
        "email": endereco,
        "entrega": convite.entrega,
        "link_primeiro_acesso": None,
    }
    # Em modo local (ou falha), a consultora vê o link para testar onboarding.
    if (
        settings.app_env == "development"
        or modo_envio() == "local"
        or convite.entrega == "FALHA"
    ):
        saida["link_primeiro_acesso"] = link
    return saida


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
    existente = _usuario_por_email(db, convite.email)
    if existente is not None and existente.senha_hash:
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


def pedir_conta_consultora(db: Session, nome: str, email: str) -> None:
    """Não cria login. O pedido espera autorização por no máximo 5 dias."""
    endereco = email_acesso(email)
    if len(nome.strip()) < 2:
        raise ErroAuth(422, "Informe o nome.")
    if _usuario_por_email(db, endereco) is not None:
        raise ErroAuth(409, "Este e-mail já tem acesso.")
    agora = _agora()
    aberto = db.scalar(
        select(PedidoConsultora).where(
            PedidoConsultora.email == endereco,
            PedidoConsultora.status == "PENDENTE",
        )
    )
    if aberto is not None:
        if (_ciente(aberto.expira_em) or agora) > agora:
            raise ErroAuth(409, "Já existe um pedido pendente para este e-mail.")
        aberto.status = "EXPIRADO"
        aberto.atualizado_em = agora
    pedido = PedidoConsultora(
        id=novo_id(),
        nome=nome.strip(),
        email=endereco,
        status="PENDENTE",
        expira_em=agora + timedelta(days=5),
        criado_em=agora,
        atualizado_em=agora,
        autorizado_em=None,
        autorizado_por_id=None,
    )
    db.add(pedido)
    _auditar(db, "PEDIDO_CONSULTORA", None)
    db.commit()


def _expirar_pedidos(db: Session) -> None:
    agora = _agora()
    abertos = db.scalars(
        select(PedidoConsultora).where(PedidoConsultora.status == "PENDENTE")
    ).all()
    for item in abertos:
        if (_ciente(item.expira_em) or agora) <= agora:
            item.status = "EXPIRADO"
            item.atualizado_em = agora


def listar_pedidos(db: Session, usuario: Usuario) -> list[PedidoConsultora]:
    if usuario.papel != "TI":
        raise ErroAuth(404, "Pedido não encontrado.")
    _expirar_pedidos(db)
    db.commit()
    return list(
        db.scalars(
            select(PedidoConsultora)
            .where(PedidoConsultora.status == "PENDENTE")
            .order_by(PedidoConsultora.criado_em.desc())
        ).all()
    )


def listar_consultores(db: Session, usuario: Usuario) -> list[Usuario]:
    if usuario.papel != "TI":
        raise ErroAuth(404, "Pedido não encontrado.")
    return list(
        db.scalars(
            select(Usuario)
            .where(
                Usuario.papel == "CONSULTOR",
                Usuario.deleted_at.is_(None),
            )
            .order_by(Usuario.nome)
        ).all()
    )


def autorizar_pedido(db: Session, operador: Usuario, pedido_id: str) -> dict[str, str]:
    """Cria a conta sem senha e manda o primeiro acesso. Só o dev autoriza.

    Se o e-mail estiver em modo local (ou a entrega falhar), devolve o link
    só para o TI — assim o teste no Render não fica preso sem Mailtrap.
    """
    if operador.papel != "TI":
        raise ErroAuth(404, "Pedido não encontrado.")
    _expirar_pedidos(db)
    pedido = db.get(PedidoConsultora, pedido_id)
    if pedido is None or pedido.status != "PENDENTE":
        raise ErroAuth(404, "Pedido não encontrado.")
    if (_ciente(pedido.expira_em) or _agora()) <= _agora():
        pedido.status = "EXPIRADO"
        pedido.atualizado_em = _agora()
        db.commit()
        raise ErroAuth(422, "Este pedido expirou.")
    if _usuario_por_email(db, pedido.email) is not None:
        raise ErroAuth(409, "Este e-mail já tem acesso.")
    agora = _agora()
    usuario = Usuario(
        nome=pedido.nome,
        email=pedido.email,
        senha_hash=None,
        papel="CONSULTOR",
        ativo=False,
        tentativas_falhas=0,
    )
    db.add(usuario)
    db.flush()
    token = novo_token_opaco()
    link = _link_com_token("primeiro-acesso.html", token)
    convite = Convite(
        email=pedido.email,
        nome=pedido.nome,
        papel="CONSULTOR",
        token_hash=hash_token(token),
        status="PENDENTE",
        entrega="NAO_ENVIADO",
        expira_em=agora + timedelta(hours=48),
        convidado_por_id=operador.id,
        projeto_id=None,
    )
    db.add(convite)
    db.flush()
    from app.integrations.email import modo_envio
    from app.services.notificacao import entregar_email

    entrega = entregar_email(
        db,
        pedido.email,
        "Horizon — primeiro acesso",
        (
            "Sua conta de consultora foi autorizada.\n"
            "Abra o link e crie sua senha. Ela não é enviada neste e-mail.\n"
            "Válido por 48 horas:\n\n"
            f"{link}\n\n"
            f"{token}\n"
        ),
        "CONVITE",
        None,
        operador.id,
    )
    convite.entrega = "ENVIADO" if entrega.status == "ENVIADO" else "FALHA"
    convite.atualizado_em = agora
    pedido.status = "AUTORIZADO"
    pedido.autorizado_em = agora
    pedido.autorizado_por_id = operador.id
    pedido.atualizado_em = agora
    _auditar(db, "CONSULTORA_AUTORIZADA", operador.id)
    db.commit()
    saida = {
        "mensagem": "Conta autorizada. O primeiro acesso foi enviado ao e-mail.",
        "email": pedido.email,
    }
    # Token só para o TI em desenvolvimento / e-mail local / falha de entrega.
    # Em produção com Mailtrap/SMTP OK, o token vai só no e-mail.
    if (
        settings.app_env == "development"
        or modo_envio() == "local"
        or entrega.status != "ENVIADO"
    ):
        saida["mensagem"] = (
            "Conta autorizada. Em desenvolvimento o link aparece aqui "
            "(válido 48h) para a consultora criar a senha. Senha nunca vai no e-mail."
        )
        saida["link_primeiro_acesso"] = link
    return saida


def reenviar_primeiro_acesso_consultora(
    db: Session, operador: Usuario, consultor_id: str
) -> dict[str, str]:
    """Novo token se a consultora ainda não definiu senha. Só o TI."""
    if operador.papel != "TI":
        raise ErroAuth(404, "Consultora não encontrada.")
    usuario = db.get(Usuario, consultor_id)
    if (
        usuario is None
        or usuario.papel != "CONSULTOR"
        or usuario.deleted_at is not None
    ):
        raise ErroAuth(404, "Consultora não encontrada.")
    if usuario.senha_hash:
        raise ErroAuth(
            422,
            "Esta consultora já definiu senha. Use recuperar senha se precisar.",
        )
    agora = _agora()
    abertos = db.scalars(
        select(Convite).where(
            Convite.email == usuario.email,
            Convite.papel == "CONSULTOR",
            Convite.status == "PENDENTE",
        )
    ).all()
    for antigo in abertos:
        antigo.status = "CANCELADO"
        antigo.atualizado_em = agora
    token = novo_token_opaco()
    link = _link_com_token("primeiro-acesso.html", token)
    convite = Convite(
        email=usuario.email,
        nome=usuario.nome,
        papel="CONSULTOR",
        token_hash=hash_token(token),
        status="PENDENTE",
        entrega="NAO_ENVIADO",
        expira_em=agora + timedelta(hours=48),
        convidado_por_id=operador.id,
        projeto_id=None,
    )
    db.add(convite)
    db.flush()
    from app.integrations.email import modo_envio
    from app.services.notificacao import entregar_email

    entrega = entregar_email(
        db,
        usuario.email,
        "Horizon — primeiro acesso",
        (
            "Reenvio do primeiro acesso da consultora.\n"
            "Abra o link e crie sua senha. Ela não é enviada neste e-mail.\n"
            "Válido por 48 horas:\n\n"
            f"{link}\n\n"
            f"{token}\n"
        ),
        "CONVITE",
        None,
        operador.id,
    )
    convite.entrega = "ENVIADO" if entrega.status == "ENVIADO" else "FALHA"
    convite.atualizado_em = agora
    _auditar(db, "CONVITE_CRIADO", operador.id)
    db.commit()
    saida = {
        "mensagem": "Primeiro acesso reenviado ao e-mail.",
        "email": usuario.email,
    }
    if (
        settings.app_env == "development"
        or modo_envio() == "local"
        or entrega.status != "ENVIADO"
    ):
        saida["mensagem"] = (
            "Novo link gerado (válido 48h). Senha nunca vai no e-mail — "
            "a consultora define no primeiro acesso."
        )
        saida["link_primeiro_acesso"] = link
    return saida


def diagnostico(db: Session, usuario: Usuario) -> dict[str, object]:
    """Estabilidade para o painel do TI. Sem senha, URL nem segredo."""
    if usuario.papel != "TI":
        raise ErroAuth(404, "Pedido não encontrado.")
    _expirar_pedidos(db)
    db.commit()
    inicio = time.perf_counter()
    banco = "ok"
    try:
        db.execute(select(func.count()).select_from(Usuario))
    except Exception:
        banco = "indisponível"
    banco_ms = int((time.perf_counter() - inicio) * 1000)
    contas = {
        papel: db.scalar(
            select(func.count())
            .select_from(Usuario)
            .where(Usuario.papel == papel, Usuario.deleted_at.is_(None))
        )
        or 0
        for papel in ("TI", "CONSULTOR", "ORGAO", "FUNCIONARIO")
    }
    recentes = db.scalars(
        select(LogAuditoria).order_by(LogAuditoria.criado_em.desc()).limit(12)
    ).all()
    from app.integrations.email import modo_envio

    email = modo_envio()
    return {
        "api": "ok",
        "banco": banco,
        "banco_ms": banco_ms,
        "email": email,
        "contas": contas,
        "pedidos_pendentes": db.scalar(
            select(func.count())
            .select_from(PedidoConsultora)
            .where(PedidoConsultora.status == "PENDENTE")
        )
        or 0,
        "projetos": db.scalar(
            select(func.count())
            .select_from(Projeto)
            .where(Projeto.deleted_at.is_(None))
        )
        or 0,
        "pesquisas": db.scalar(select(func.count()).select_from(Pesquisa)) or 0,
        "auditoria": [
            {"acao": item.acao, "criado_em": item.criado_em.isoformat()}
            for item in recentes
        ],
    }


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
