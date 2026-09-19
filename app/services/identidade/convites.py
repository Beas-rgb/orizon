"""Convites e links de primeiro acesso."""

from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import url_publica
from app.core.tokens import hash_token, novo_token_opaco
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
    saida: dict[str, str | None] = {
        "email": endereco,
        "entrega": convite.entrega,
        "link_primeiro_acesso": None,
    }
    if _expor_link_primeiro_acesso(entrega_ok=convite.entrega == "ENVIADO"):
        saida["link_primeiro_acesso"] = link
    return saida
