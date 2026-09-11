"""Aviso interno e entrega. E-mail sai agora. Telefone só reserva o canal.

O texto gravado nunca leva token, senha ou nome de quem respondeu a pesquisa.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.integrations.email import caixa_email
from app.models.auditoria import LogAuditoria
from app.models.base import agora
from app.models.notificacao import EntregaMensagem, Notificacao
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.usuario import Usuario

CANAIS = {"EMAIL", "TELEFONE"}
TIPOS = {"CONVITE", "PESQUISA", "DOCUMENTO", "SISTEMA"}


def _auditar(db: Session, acao: str, usuario_id: str | None) -> None:
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=usuario_id,
            acao=acao,
            criado_em=agora(),
        )
    )


def avisar(
    db: Session,
    usuario: Usuario,
    tipo: str,
    titulo: str,
    mensagem: str,
    projeto_id: str | None = None,
    canal: str = "EMAIL",
    referencia: str = "SISTEMA",
) -> Notificacao:
    """Cria o aviso interno e tenta a entrega no canal pedido."""
    from app.services.identidade import ErroAuth

    if tipo not in TIPOS:
        raise ErroAuth(422, "Tipo de aviso inválido.")
    if canal not in CANAIS:
        raise ErroAuth(422, "Canal inválido.")
    aviso = Notificacao(
        id=novo_id(),
        usuario_id=usuario.id,
        projeto_id=projeto_id,
        tipo=tipo,
        titulo=titulo[:160],
        mensagem=mensagem,
        lida=False,
        lida_em=None,
        criado_em=agora(),
        deleted_at=None,
        prioridade="normal",
    )
    db.add(aviso)
    if canal == "EMAIL" and usuario.email:
        entregar_email(
            db,
            usuario.email,
            titulo,
            mensagem,
            referencia,
            projeto_id,
            usuario.id,
        )
    elif canal == "TELEFONE":
        reservar_telefone(
            db,
            usuario.telefone or "",
            titulo,
            referencia,
            projeto_id,
            usuario.id,
        )
    return aviso


def entregar_email(
    db: Session,
    destino: str,
    assunto: str,
    corpo: str,
    referencia: str,
    projeto_id: str | None = None,
    usuario_id: str | None = None,
) -> EntregaMensagem:
    """Envia o e-mail e grava só o status. O corpo com token não fica no banco."""
    agora_ = agora()
    entrega = EntregaMensagem(
        id=novo_id(),
        canal="EMAIL",
        destino=destino,
        assunto=assunto[:160],
        status="PENDENTE",
        referencia=referencia,
        projeto_id=projeto_id,
        usuario_id=usuario_id,
        erro=None,
        criado_em=agora_,
        atualizado_em=agora_,
        enviado_em=None,
    )
    db.add(entrega)
    try:
        caixa_email.enviar(destino, assunto, corpo, categoria=referencia)
    except Exception:
        entrega.status = "FALHA"
        entrega.erro = "Falha ao enviar e-mail."
        entrega.atualizado_em = agora()
        return entrega
    entrega.status = "ENVIADO"
    entrega.enviado_em = agora()
    entrega.atualizado_em = entrega.enviado_em
    return entrega


def reservar_telefone(
    db: Session,
    destino: str,
    assunto: str,
    referencia: str,
    projeto_id: str | None = None,
    usuario_id: str | None = None,
) -> EntregaMensagem:
    """Não chama provedor. O número fica reservado para a integração futura."""
    agora_ = agora()
    entrega = EntregaMensagem(
        id=novo_id(),
        canal="TELEFONE",
        destino=destino,
        assunto=assunto[:160],
        status="NAO_HABILITADO",
        referencia=referencia,
        projeto_id=projeto_id,
        usuario_id=usuario_id,
        erro="SMS ainda não habilitado.",
        criado_em=agora_,
        atualizado_em=agora_,
        enviado_em=None,
    )
    db.add(entrega)
    _auditar(db, "TELEFONE_NAO_HABILITADO", usuario_id)
    return entrega


def listar(db: Session, usuario: Usuario) -> list[Notificacao]:
    return list(
        db.scalars(
            select(Notificacao)
            .where(
                Notificacao.usuario_id == usuario.id,
                Notificacao.deleted_at.is_(None),
            )
            .order_by(Notificacao.criado_em.desc())
        ).all()
    )


def marcar_lida(db: Session, usuario: Usuario, aviso_id: str) -> Notificacao:
    from app.services.identidade import ErroAuth

    aviso = db.get(Notificacao, aviso_id)
    if (
        aviso is None
        or aviso.deleted_at is not None
        or aviso.usuario_id != usuario.id
    ):
        raise ErroAuth(404, "Aviso não encontrado.")
    if not aviso.lida:
        aviso.lida = True
        aviso.lida_em = agora()
        _auditar(db, "NOTIFICACAO_LIDA", usuario.id)
        db.commit()
    return aviso


def listar_entregas(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
) -> list[EntregaMensagem]:
    from app.services.identidade import ErroAuth

    projeto = db.get(Projeto, projeto_id)
    if (
        projeto is None
        or projeto.deleted_at is not None
        or usuario.id != projeto.consultor_id
    ):
        vinculo = db.scalar(
            select(ProjetoUsuario).where(
                ProjetoUsuario.projeto_id == projeto_id,
                ProjetoUsuario.usuario_id == usuario.id,
                ProjetoUsuario.papel == "CONSULTOR",
            )
        )
        if vinculo is None:
            raise ErroAuth(404, "Projeto não encontrado.")
    return list(
        db.scalars(
            select(EntregaMensagem)
            .where(EntregaMensagem.projeto_id == projeto_id)
            .order_by(EntregaMensagem.criado_em.desc())
        ).all()
    )


def membros_orgao(db: Session, projeto_id: str) -> list[Usuario]:
    return list(
        db.scalars(
            select(Usuario)
            .join(ProjetoUsuario, ProjetoUsuario.usuario_id == Usuario.id)
            .where(
                ProjetoUsuario.projeto_id == projeto_id,
                ProjetoUsuario.papel == "ORGAO",
                Usuario.deleted_at.is_(None),
                Usuario.ativo.is_(True),
            )
        ).all()
    )
