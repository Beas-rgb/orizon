"""Aviso interno e entrega. E-mail sai agora. Telefone só reserva o canal.

O texto gravado nunca leva token, senha ou nome de quem respondeu a pesquisa.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.integrations.email import ResultadoEmail, caixa_email, modo_envio
from app.models.base import agora
from app.models.notificacao import EntregaMensagem, Notificacao
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.usuario import Usuario
from app.services.auditoria import registrar as _auditar

CANAIS = {"EMAIL", "TELEFONE"}
TIPOS = {"CONVITE", "PESQUISA", "DOCUMENTO", "SISTEMA"}
STATUS_EMAIL_OK = {"ACEITO", "ENVIADO"}


def entrega_aceita(entrega: EntregaMensagem) -> bool:
    return entrega.status in STATUS_EMAIL_OK


def _registrar_aceite(
    entrega: EntregaMensagem,
    resultado: ResultadoEmail,
) -> None:
    """Registra aceite técnico sem chamar de entrega confirmada."""
    entrega.provedor = resultado.provedor
    entrega.provedor_mensagem_id = resultado.mensagem_id
    entrega.status = "ENVIADO" if resultado.provedor == "local" else "ACEITO"
    entrega.erro = None
    entrega.enviado_em = agora()
    entrega.atualizado_em = entrega.enviado_em


def avisar(
    db: Session,
    usuario: Usuario,
    tipo: str,
    titulo: str,
    mensagem: str,
    projeto_id: str | None = None,
    canal: str = "EMAIL",
    referencia: str = "SISTEMA",
    *,
    tarefas=None,
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
            tarefas=tarefas,
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


def _completar_entrega_email(
    entrega_id: str,
    destino: str,
    assunto: str,
    corpo: str,
    categoria: str,
) -> None:
    """Roda fora do request: SMTP não segura o pool da API.

    Abre uma sessão nova. Se o ambiente já vinculou um engine (teste
    SQLite ou o primeiro get_engine de produção), usa essa fábrica.
    Não reutiliza a Session do request.
    """
    from app.core import database as banco

    if banco.SessionLocal is None:
        banco.get_engine()
    if banco.SessionLocal is None:
        return
    resultado: ResultadoEmail | None = None
    erro = None
    try:
        resultado = caixa_email.enviar(
            destino,
            assunto,
            corpo,
            categoria=categoria,
        )
    except Exception as exc:
        erro = _erro_entrega_seguro(exc)
    with banco.SessionLocal() as db:
        entrega = db.get(EntregaMensagem, entrega_id)
        if entrega is None:
            return
        if resultado is not None:
            _registrar_aceite(entrega, resultado)
        else:
            entrega.status = "FALHA"
            entrega.erro = erro
            entrega.atualizado_em = agora()
        db.commit()


def entregar_email(
    db: Session,
    destino: str,
    assunto: str,
    corpo: str,
    referencia: str,
    projeto_id: str | None = None,
    usuario_id: str | None = None,
    *,
    tarefas=None,
) -> EntregaMensagem:
    """Envia o e-mail e grava só o status. O corpo com token não fica no banco.

    Com `tarefas` (BackgroundTasks), o SMTP sai depois da resposta HTTP.
    """
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
        provedor=modo_envio(),
        provedor_mensagem_id=None,
        criado_em=agora_,
        atualizado_em=agora_,
        enviado_em=None,
    )
    db.add(entrega)
    db.flush()
    if tarefas is not None:
        tarefas.add_task(
            _completar_entrega_email,
            entrega.id,
            destino,
            assunto,
            corpo,
            referencia,
        )
        return entrega
    try:
        resultado = caixa_email.enviar(
            destino,
            assunto,
            corpo,
            categoria=referencia,
        )
    except Exception as exc:
        entrega.status = "FALHA"
        entrega.erro = _erro_entrega_seguro(exc)
        entrega.atualizado_em = agora()
        return entrega
    _registrar_aceite(entrega, resultado)
    return entrega


def _erro_entrega_seguro(exc: BaseException) -> str:
    """Mensagem curta para o TI. Sem token, senha nem URL de banco."""
    bruto = " ".join(str(exc).split())
    baixo = bruto.lower()
    if any(
        chave in baixo
        for chave in (
            "network is unreachable",
            "errno 101",
            "enetunreach",
            "timed out",
            "etimedout",
        )
    ):
        return (
            "Falha de rede SMTP. No Render free as portas 587/465 são "
            "bloqueadas — use SendGrid (API HTTPS)."
        )
    if any(
        chave in baixo
        for chave in (
            "unauthorized",
            "forbidden",
            "401",
            "403",
            "invalid api",
            "invalid token",
        )
    ):
        return "Falha: token ou permissão inválidos no provedor de e-mail."
    if any(
        chave in baixo
        for chave in (
            "sender",
            "from",
            "domain",
            "not verified",
            "not allowed",
            "remetente",
        )
    ):
        return (
            "Falha: remetente não verificado no provedor. "
            "No SendGrid use Single Sender Verification."
        )
    if "remetente sendgrid não configurado" in baixo:
        return "Falha: SENDGRID_FROM_EMAIL não configurado."
    if "remetente mailtrap não configurado" in baixo:
        return "Falha: MAILTRAP_FROM_EMAIL não configurado."
    if not bruto:
        return "Falha ao enviar e-mail."
    limpo = bruto[:160]
    for trecho in ("Bearer ", "token=", "api_key=", "password=", "postgres://"):
        if trecho.lower() in limpo.lower():
            return "Falha ao enviar e-mail."
    return f"Falha ao enviar e-mail: {limpo}"


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
        provedor=None,
        provedor_mensagem_id=None,
        criado_em=agora_,
        atualizado_em=agora_,
        enviado_em=None,
    )
    db.add(entrega)
    _auditar(db, "TELEFONE_NAO_HABILITADO", usuario_id)
    return entrega


def listar(
    db: Session,
    usuario: Usuario,
    *,
    limite: int = 50,
    deslocamento: int = 0,
) -> list[Notificacao]:
    limite = max(1, min(limite, 100))
    deslocamento = max(0, deslocamento)
    return list(
        db.scalars(
            select(Notificacao)
            .where(
                Notificacao.usuario_id == usuario.id,
                Notificacao.deleted_at.is_(None),
            )
            .order_by(Notificacao.criado_em.desc())
            .offset(deslocamento)
            .limit(limite)
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
    *,
    limite: int = 50,
    deslocamento: int = 0,
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
    limite = max(1, min(limite, 100))
    deslocamento = max(0, deslocamento)
    return list(
        db.scalars(
            select(EntregaMensagem)
            .where(EntregaMensagem.projeto_id == projeto_id)
            .order_by(EntregaMensagem.criado_em.desc())
            .offset(deslocamento)
            .limit(limite)
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


def notificar_novo_trabalho_orgao(
    db: Session,
    orgao: Usuario,
    projeto: Projeto,
    *,
    tarefas=None,
) -> Notificacao:
    """Aviso a ORGAO já ativo: novo projeto, sem primeiro acesso/token."""
    from app.core.config import url_entrar_com_next
    from app.models.organizacao import Organizacao

    org = db.get(Organizacao, projeto.organizacao_id)
    nome_cliente = ""
    if org is not None:
        nome_cliente = (org.nome_fantasia or org.razao_social or "").strip()
    destino = f"/projetos/{projeto.id}"
    link = url_entrar_com_next(destino)
    titulo = "Orizon — novo trabalho disponível"
    mensagem = (
        f"Olá, {orgao.nome.strip()}.\n\n"
        "Um novo trabalho foi vinculado à sua conta no Orizon.\n"
        f"{('Cliente: ' + nome_cliente + chr(10)) if nome_cliente else ''}"
        f"Referência: {projeto.vinculo_titulo or projeto.id}.\n\n"
        "Entre com a senha que você já cadastrou:\n"
        f"{link}\n\n"
        "Não é necessário criar outra conta."
    )
    return avisar(
        db,
        orgao,
        "SISTEMA",
        titulo,
        mensagem,
        projeto.id,
        "EMAIL",
        "AVISO_NOVO_TRABALHO",
        tarefas=tarefas,
    )


def notificar_nova_pesquisa(
    db: Session,
    usuario: Usuario,
    pesquisa,
    *,
    tarefas=None,
) -> Notificacao:
    """Aviso reutilizável (CLIMA/DESEMPENHO/DIAGNOSTICO): conta já existe."""
    from app.core.config import url_entrar_com_next

    prazo = ""
    if getattr(pesquisa, "disponivel_ate", None) is not None:
        prazo = (
            f"Prazo até {pesquisa.disponivel_ate.strftime('%d/%m/%Y')}.\n"
        )
    destino = f"/projetos/{pesquisa.projeto_id}"
    link = url_entrar_com_next(destino)
    titulo = "Orizon — nova pesquisa disponível"
    mensagem = (
        f"Olá, {usuario.nome.strip()}.\n\n"
        f"A pesquisa «{pesquisa.titulo}» está disponível.\n"
        f"{prazo}"
        "Entre com sua conta existente:\n"
        f"{link}\n\n"
        "Não enviamos senha nem link de primeiro acesso."
    )
    return avisar(
        db,
        usuario,
        "PESQUISA",
        titulo,
        mensagem,
        pesquisa.projeto_id,
        "EMAIL",
        "AVISO_NOVA_PESQUISA",
        tarefas=tarefas,
    )
