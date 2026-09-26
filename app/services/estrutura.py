"""Estrutura organizacional do projeto: cargo e hierarquia.

Setor segmenta. Superior define a árvore. Um ciclo (A→B→A) é rejeitado.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.autorizacao import exigir_papel
from app.core.tokens import novo_id
from app.models.base import agora
from app.models.estrutura import Cargo, PerfilFuncionario
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.setor import Setor
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth


def _projeto_da_consultora(db: Session, consultor: Usuario, projeto_id: str) -> Projeto:
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    projeto = db.get(Projeto, projeto_id)
    if (
        projeto is None
        or projeto.deleted_at is not None
        or projeto.consultor_id != consultor.id
    ):
        raise ErroAuth(404, "Projeto não encontrado.")
    return projeto


def criar_cargo(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    nome: str,
) -> Cargo:
    _projeto_da_consultora(db, consultor, projeto_id)
    limpo = nome.strip()
    if len(limpo) < 2:
        raise ErroAuth(422, "Informe o cargo.")
    ja = db.scalar(
        select(Cargo).where(
            Cargo.projeto_id == projeto_id,
            Cargo.nome == limpo,
            Cargo.deleted_at.is_(None),
        )
    )
    if ja is not None:
        raise ErroAuth(409, "Este cargo já existe neste projeto.")
    cargo = Cargo(
        id=novo_id(),
        projeto_id=projeto_id,
        nome=limpo[:120],
        criado_em=agora(),
        atualizado_em=agora(),
        deleted_at=None,
    )
    db.add(cargo)
    db.commit()
    return cargo


def listar_cargos(db: Session, usuario: Usuario, projeto_id: str) -> list[Cargo]:
    exigir_papel(db, usuario, projeto_id, {"CONSULTOR", "ORGAO"})
    return list(
        db.scalars(
            select(Cargo)
            .where(Cargo.projeto_id == projeto_id, Cargo.deleted_at.is_(None))
            .order_by(Cargo.nome)
        ).all()
    )


def _superior_valido(
    db: Session,
    projeto_id: str,
    usuario_id: str,
    superior_id: str | None,
) -> None:
    """Não deixa A→A nem ciclo A→B→A."""
    if superior_id is None:
        return
    if superior_id == usuario_id:
        raise ErroAuth(422, "O funcionário não pode ser o próprio superior.")
    superior = db.get(Usuario, superior_id)
    if superior is None or superior.deleted_at is not None or not superior.ativo:
        raise ErroAuth(404, "Superior não encontrado.")
    membro = db.scalar(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.usuario_id == superior_id,
            ProjetoUsuario.papel == "FUNCIONARIO",
        )
    )
    if membro is None:
        raise ErroAuth(404, "Superior não encontrado.")
    vinculo = db.scalar(
        select(PerfilFuncionario).where(
            PerfilFuncionario.projeto_id == projeto_id,
            PerfilFuncionario.usuario_id == superior_id,
            PerfilFuncionario.deleted_at.is_(None),
        )
    )
    if vinculo is None:
        # O superior ainda não tem perfil. Cria um mínimo para a cadeia subir.
        agora_ = agora()
        vinculo = PerfilFuncionario(
            id=novo_id(),
            projeto_id=projeto_id,
            usuario_id=superior_id,
            setor_id=None,
            cargo_id=None,
            superior_id=None,
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
        db.add(vinculo)
        db.flush()
    # Sobe a cadeia. Se voltar ao usuário, é ciclo.
    atual = superior_id
    vistos = {usuario_id}
    while atual is not None:
        if atual in vistos:
            raise ErroAuth(422, "A hierarquia não pode formar ciclo.")
        vistos.add(atual)
        perfil = db.scalar(
            select(PerfilFuncionario).where(
                PerfilFuncionario.projeto_id == projeto_id,
                PerfilFuncionario.usuario_id == atual,
                PerfilFuncionario.deleted_at.is_(None),
            )
        )
        atual = perfil.superior_id if perfil else None


def definir_perfil_funcionario(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    usuario_id: str,
    *,
    setor_id: str | None = None,
    cargo_id: str | None = None,
    superior_id: str | None = None,
) -> PerfilFuncionario:
    """Cria ou atualiza o vínculo organizacional. Idempotente por projeto."""
    _projeto_da_consultora(db, consultor, projeto_id)
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or usuario.deleted_at is not None or not usuario.ativo:
        raise ErroAuth(404, "Funcionário não encontrado.")
    if setor_id is not None:
        setor = db.get(Setor, setor_id)
        if (
            setor is None
            or setor.deleted_at is not None
            or setor.projeto_id != projeto_id
        ):
            raise ErroAuth(422, "Setor não pertence a este projeto.")
    if cargo_id is not None:
        cargo = db.get(Cargo, cargo_id)
        if (
            cargo is None
            or cargo.deleted_at is not None
            or cargo.projeto_id != projeto_id
        ):
            raise ErroAuth(422, "Cargo não pertence a este projeto.")
    _superior_valido(db, projeto_id, usuario_id, superior_id)
    perfil = db.scalar(
        select(PerfilFuncionario).where(
            PerfilFuncionario.projeto_id == projeto_id,
            PerfilFuncionario.usuario_id == usuario_id,
            PerfilFuncionario.deleted_at.is_(None),
        )
    )
    agora_ = agora()
    if perfil is None:
        perfil = PerfilFuncionario(
            id=novo_id(),
            projeto_id=projeto_id,
            usuario_id=usuario_id,
            setor_id=setor_id,
            cargo_id=cargo_id,
            superior_id=superior_id,
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
        db.add(perfil)
    else:
        perfil.setor_id = setor_id
        perfil.cargo_id = cargo_id
        perfil.superior_id = superior_id
        perfil.atualizado_em = agora_
    db.commit()
    return perfil


def listar_perfis(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
) -> list[PerfilFuncionario]:
    exigir_papel(db, usuario, projeto_id, {"CONSULTOR", "ORGAO"})
    return list(
        db.scalars(
            select(PerfilFuncionario)
            .where(
                PerfilFuncionario.projeto_id == projeto_id,
                PerfilFuncionario.deleted_at.is_(None),
            )
            .order_by(PerfilFuncionario.criado_em)
        ).all()
    )


def arvore_hierarquica(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
) -> list[dict[str, object]]:
    """Raízes e subordinados, derivados de superior_id."""
    perfis = listar_perfis(db, usuario, projeto_id)
    por_superior: dict[str | None, list[PerfilFuncionario]] = {}
    for perfil in perfis:
        por_superior.setdefault(perfil.superior_id, []).append(perfil)

    def montar(perfil: PerfilFuncionario) -> dict[str, object]:
        pessoa = db.get(Usuario, perfil.usuario_id)
        cargo = db.get(Cargo, perfil.cargo_id) if perfil.cargo_id else None
        setor = db.get(Setor, perfil.setor_id) if perfil.setor_id else None
        return {
            "usuario_id": perfil.usuario_id,
            "nome": pessoa.nome if pessoa else "",
            "email": pessoa.email if pessoa else "",
            "cargo": cargo.nome if cargo else None,
            "setor": setor.nome if setor else None,
            "subordinados": [
                montar(filho)
                for filho in por_superior.get(perfil.usuario_id, [])
            ],
        }

    return [montar(raiz) for raiz in por_superior.get(None, [])]
