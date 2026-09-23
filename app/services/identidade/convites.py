"""Convites e links de primeiro acesso."""

from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import url_publica
from app.core.tokens import hash_token, novo_id, novo_token_opaco
from app.models.convite import Convite
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.usuario import Usuario

from .erros import (
    MSG_ESPERA,
    PAPEIS,
    ErroAuth,
    _agora,
    _auditar,
    _usuario_por_email,
    email_acesso,
    limpar_falhas,
    registrar_falha,
    segundos_bloqueio,
    settings,
)

# Situações de resolver_usuario_orgao_por_email
SIT_NOVO = "novo"
SIT_ORGAO_ATIVO = "orgao_ativo"
SIT_ORGAO_INATIVO = "orgao_inativo"
SIT_CONFLITO = "conflito"


@dataclass(frozen=True)
class ResolucaoOrgao:
    """Resultado interno: não expor em JSON público sem filtrar."""

    situacao: str
    usuario: Usuario | None = None
    papel_conflito: str | None = None
    email: str = ""


def resolver_usuario_orgao_por_email(db: Session, email: str) -> ResolucaoOrgao:
    """Classifica o e-mail para onboarding de órgão (sem efeito colateral)."""
    endereco = email_acesso(email)
    usuario = _usuario_por_email(db, endereco)
    if usuario is None:
        return ResolucaoOrgao(situacao=SIT_NOVO, email=endereco)
    if usuario.papel == "ORGAO":
        if usuario.ativo:
            return ResolucaoOrgao(
                situacao=SIT_ORGAO_ATIVO,
                usuario=usuario,
                email=endereco,
            )
        return ResolucaoOrgao(
            situacao=SIT_ORGAO_INATIVO,
            usuario=usuario,
            email=endereco,
        )
    return ResolucaoOrgao(
        situacao=SIT_CONFLITO,
        usuario=usuario,
        papel_conflito=usuario.papel,
        email=endereco,
    )


def vincular_orgao_existente_ao_projeto(
    db: Session,
    consultor: Usuario,
    projeto: Projeto,
    usuario: Usuario,
) -> bool:
    """Garante ProjetoUsuario ORGAO. Idempotente. Devolve True se criou agora.

    Não reativa conta inativa. Não troca papel. Exige consultora dona do projeto.
    """
    if consultor.papel != "CONSULTOR" or projeto.consultor_id != consultor.id:
        raise ErroAuth(404, "Projeto não encontrado.")
    if projeto.deleted_at is not None:
        raise ErroAuth(404, "Projeto não encontrado.")
    if usuario.papel != "ORGAO":
        raise ErroAuth(422, "Só conta de órgão pode ser vinculada assim.")
    if not usuario.ativo or usuario.deleted_at is not None:
        raise ErroAuth(422, "Conta de órgão inativa. Peça reativação ao TI.")
    ja = db.scalar(
        select(ProjetoUsuario.id).where(
            ProjetoUsuario.projeto_id == projeto.id,
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    if ja is not None:
        return False
    db.add(
        ProjetoUsuario(
            id=novo_id(),
            projeto_id=projeto.id,
            usuario_id=usuario.id,
            papel="ORGAO",
        )
    )
    _auditar(db, "ORGAO_VINCULADO", consultor.id)
    return True


def _link_com_token(pagina: str, token: str) -> str:
    """Link do React em /app. Nunca aponta para HTML legado.

    Usa `?t=` (não só `#`): vários clientes de e-mail removem o fragmento
    e a pessoa abria a tela sem o token.
    """
    base = url_publica().rstrip("/")
    # pagina legado → rota React equivalente
    rotas = {
        "primeiro-acesso.html": "primeiro-acesso",
        "redefinir.html": "recuperar",
        "primeiro-acesso": "primeiro-acesso",
        "recuperar": "recuperar",
    }
    caminho = rotas.get(pagina, pagina.removesuffix(".html"))
    return f"{base}/{caminho}?t={quote(token, safe='')}"


def _corpo_primeiro_acesso(
    nome: str,
    link: str,
    token: str,
    *,
    contexto: str,
) -> str:
    """Mensagem clara, com um CTA e código manual no fim."""
    return (
        f"Olá, {nome.strip()}.\n\n"
        f"{contexto}\n"
        "Para proteger sua conta, a senha será criada por você.\n\n"
        "ABRIR PRIMEIRO ACESSO:\n"
        f"{link}\n\n"
        "Este acesso é pessoal e expira em 48 horas. "
        "Não encaminhe esta mensagem.\n"
        "Se você não esperava este convite, ignore o e-mail.\n\n"
        "Se o botão/link não abrir, cole este código na tela de primeiro acesso:\n"
        f"{token}"
    )


def _expor_link_primeiro_acesso(
    *,
    entrega_ok: bool,
    para_ti: bool = False,
) -> bool:
    """Quando devolver o link no JSON.

    - Rotas do TI (`para_ti`): sempre — o operador precisa testar/onboard
      sem depender só da caixa de entrada.
    - Demais rotas em production: nunca (token só no e-mail).
    - development / modo local / falha de envio: sim.
    """
    if para_ti:
        return True
    if settings.app_env == "production":
        return False
    from app.integrations.email import modo_envio

    return (
        settings.app_env == "development"
        or modo_envio() == "local"
        or not entrega_ok
    )


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
    from app.services.notificacao import entrega_aceita, entregar_email

    entrega = entregar_email(
        db,
        endereco,
        "Seu primeiro acesso ao Horizon",
        _corpo_primeiro_acesso(
            nome.strip(),
            link,
            token,
            contexto="Você recebeu um convite para acessar o Horizon.",
        ),
        "CONVITE",
        projeto_id,
        consultor.id,
    )
    convite.entrega = "ENVIADO" if entrega_aceita(entrega) else "FALHA"
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
    saida: dict[str, str | None] = {
        "email": endereco,
        "entrega": convite.entrega,
        "link_primeiro_acesso": None,
    }
    if _expor_link_primeiro_acesso(entrega_ok=convite.entrega == "ENVIADO"):
        saida["link_primeiro_acesso"] = link
    return saida
