"""Pedidos de conta consultora e painel de diagnóstico do TI."""

import time
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tokens import hash_token, novo_id, novo_token_opaco
from app.models.auditoria import LogAuditoria
from app.models.convite import Convite
from app.models.pedido_consultora import PedidoConsultora
from app.models.pesquisa import Pesquisa
from app.models.projeto import Projeto
from app.models.usuario import Usuario

from .convites import _expor_link_primeiro_acesso, _link_com_token
from .erros import (
    ErroAuth,
    _agora,
    _auditar,
    _ciente,
    _exigir_rate_publico,
    _usuario_por_email,
    _usuario_soft_por_email,
    email_acesso,
    registrar_falha,
)


def pedir_conta_consultora(
    db: Session,
    nome: str,
    email: str,
    *,
    ip: str | None = None,
) -> None:
    """Não cria login. O pedido espera autorização por no máximo 5 dias."""
    endereco = email_acesso(email)
    chave_email = f"cadastro-consultora:email:{endereco}"
    chave_ip = f"cadastro-consultora:ip:{ip}" if ip else ""
    _exigir_rate_publico(db, chave_email, chave_ip)
    if len(nome.strip()) < 2:
        registrar_falha(db, chave_email)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
        raise ErroAuth(422, "Informe o nome.")
    if _usuario_por_email(db, endereco) is not None:
        registrar_falha(db, chave_email)
        if chave_ip:
            registrar_falha(db, chave_ip)
        db.commit()
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
            registrar_falha(db, chave_email)
            if chave_ip:
                registrar_falha(db, chave_ip)
            db.commit()
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
    registrar_falha(db, chave_email)
    if chave_ip:
        registrar_falha(db, chave_ip)
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
    # Soft-delete anterior deixa o e-mail no unique: reativa em vez de INSERT.
    usuario = _usuario_soft_por_email(db, pedido.email)
    if usuario is not None:
        usuario.nome = pedido.nome
        usuario.senha_hash = None
        usuario.papel = "CONSULTOR"
        usuario.ativo = False
        usuario.tentativas_falhas = 0
        usuario.bloqueado_ate = None
        usuario.deleted_at = None
        usuario.atualizado_em = agora
    else:
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
    if _expor_link_primeiro_acesso(
        entrega_ok=entrega.status == "ENVIADO",
        para_ti=True,
    ):
        if entrega.status != "ENVIADO":
            saida["mensagem"] = (
                "Conta autorizada, mas o e-mail falhou. Use o link abaixo "
                "(válido 48h). Senha nunca vai no e-mail."
            )
            saida["aviso_email"] = entrega.erro or "Falha ao enviar e-mail."
        else:
            saida["mensagem"] = (
                "Conta autorizada. O e-mail foi enviado; o link também "
                "aparece aqui para o TI (válido 48h). "
                "Senha nunca vai no e-mail."
            )
        saida["link_primeiro_acesso"] = link
    elif entrega.status != "ENVIADO":
        saida["mensagem"] = (
            "Conta autorizada, mas o e-mail falhou. "
            "Peça reenvio do primeiro acesso."
        )
        saida["aviso_email"] = entrega.erro or "Falha ao enviar e-mail."
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
    if _expor_link_primeiro_acesso(
        entrega_ok=entrega.status == "ENVIADO",
        para_ti=True,
    ):
        if entrega.status != "ENVIADO":
            saida["mensagem"] = (
                "E-mail falhou. Novo link gerado (válido 48h) — use o link abaixo. "
                "Senha nunca vai no e-mail."
            )
            saida["aviso_email"] = entrega.erro or "Falha ao enviar e-mail."
        else:
            saida["mensagem"] = (
                "Novo link gerado (válido 48h). Senha nunca vai no e-mail — "
                "a consultora define no primeiro acesso."
            )
        saida["link_primeiro_acesso"] = link
    elif entrega.status != "ENVIADO":
        saida["mensagem"] = (
            "E-mail falhou. Peça outro reenvio do primeiro acesso."
        )
        saida["aviso_email"] = entrega.erro or "Falha ao enviar e-mail."
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
