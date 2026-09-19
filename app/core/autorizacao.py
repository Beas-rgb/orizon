"""Autorização única por projeto/recurso.

Toda checagem de “este usuário acessa este projeto?” passa por aqui.
Falha → sempre 404 (não confirma existência do recurso).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pesquisa import Pesquisa
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth

MSG_404_PROJETO = "Projeto não encontrado."
MSG_404_PESQUISA = "Pesquisa não encontrada."
MSG_404_MIDIA = "Mídia não encontrada."


def papel_no_projeto(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
) -> str | None:
    """CONSULTOR / ORGAO / FUNCIONARIO se o vínculo existir; senão None.

    TI nunca recebe papel de projeto (não enumera projetos).
    """
    if usuario.papel == "TI":
        return None
    projeto = db.get(Projeto, projeto_id)
    if projeto is None or projeto.deleted_at is not None:
        return None
    if usuario.id == projeto.consultor_id:
        return "CONSULTOR"
    vinculo = db.scalar(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    return vinculo.papel if vinculo else None


def participa(db: Session, usuario: Usuario, projeto_id: str) -> bool:
    return papel_no_projeto(db, usuario, projeto_id) is not None


def exigir_papel(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
    papeis: set[str],
    *,
    mensagem: str = MSG_404_PROJETO,
) -> str:
    """Garante que o usuário tem um dos papéis no projeto. Senão 404."""
    papel = papel_no_projeto(db, usuario, projeto_id)
    if papel is None or papel not in papeis:
        raise ErroAuth(404, mensagem)
    return papel


def exigir_pesquisa_viva(db: Session, pesquisa_id: str) -> Pesquisa:
    pesquisa = db.get(Pesquisa, pesquisa_id)
    if pesquisa is None or pesquisa.deleted_at is not None:
        raise ErroAuth(404, MSG_404_PESQUISA)
    return pesquisa


def exigir_midia_pesquisa(
    db: Session,
    usuario: Usuario,
    pesquisa: Pesquisa,
) -> str:
    """Consultora sempre (rascunho incluso). Órgão/funcionário só publicada/encerrada."""
    papel = exigir_papel(
        db,
        usuario,
        pesquisa.projeto_id,
        {"CONSULTOR", "ORGAO", "FUNCIONARIO"},
        mensagem=MSG_404_MIDIA,
    )
    if papel == "CONSULTOR":
        return papel
    if pesquisa.status not in {"PUBLICADA", "ENCERRADA"}:
        raise ErroAuth(404, MSG_404_MIDIA)
    return papel
