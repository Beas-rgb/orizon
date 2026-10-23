"""Estrutura organizacional do projeto: cargo e hierarquia.

Setor segmenta. Superior define a árvore. Um ciclo (A→B→A) é rejeitado.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.autorizacao import exigir_papel
from app.core.database import serializar_no_sqlite
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


def listar_cargos(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
    *,
    limite: int = 500,
    deslocamento: int = 0,
) -> list[Cargo]:
    exigir_papel(db, usuario, projeto_id, {"CONSULTOR", "ORGAO"})
    return list(
        db.scalars(
            select(Cargo)
            .where(Cargo.projeto_id == projeto_id, Cargo.deleted_at.is_(None))
            .order_by(Cargo.nome, Cargo.id)
            .limit(min(max(limite, 1), 500))
            .offset(max(deslocamento, 0))
        ).all()
    )


def _membro_funcionario(db: Session, projeto_id: str, usuario_id: str) -> bool:
    """True só se a pessoa é FUNCIONARIO deste projeto."""
    return (
        db.scalar(
            select(ProjetoUsuario.id).where(
                ProjetoUsuario.projeto_id == projeto_id,
                ProjetoUsuario.usuario_id == usuario_id,
                ProjetoUsuario.papel == "FUNCIONARIO",
            )
        )
        is not None
    )


def membros_ativos(
    db: Session, projeto_id: str, *, so_com_acesso: bool = False
) -> set[str]:
    """FUNCIONARIO do projeto, fora conta apagada.

    A geração pede so_com_acesso: só quem já pode entrar.
    Árvore e lista escondem quem foi desligado (inativo e já tem senha)
    e mantêm o importado que ainda não fez o primeiro acesso.
    """
    consulta = (
        select(Usuario.id)
        .join(ProjetoUsuario, ProjetoUsuario.usuario_id == Usuario.id)
        .where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.papel == "FUNCIONARIO",
            Usuario.deleted_at.is_(None),
        )
    )
    if so_com_acesso:
        consulta = consulta.where(Usuario.ativo.is_(True))
    else:
        consulta = consulta.where(
            or_(Usuario.ativo.is_(True), Usuario.senha_hash.is_(None))
        )
    return set(db.scalars(consulta).all())


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
    if not _membro_funcionario(db, projeto_id, superior_id):
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
    # Depois de setor/cargo: um cargo de outro projeto continua 422.
    # Antes de gravar: sem vínculo FUNCIONARIO, nada é persistido.
    if not _membro_funcionario(db, projeto_id, usuario_id):
        raise ErroAuth(404, "Funcionário não encontrado.")
    _superior_valido(db, projeto_id, usuario_id, superior_id)
    dados = {"setor_id": setor_id, "cargo_id": cargo_id, "superior_id": superior_id}
    with serializar_no_sqlite(db):
        try:
            return _gravar_perfil(db, projeto_id, usuario_id, dados)
        except IntegrityError:
            # Outra sessão criou o perfil entre a leitura e o commit.
            db.rollback()
            return _gravar_perfil(db, projeto_id, usuario_id, dados)


def _gravar_perfil(
    db: Session,
    projeto_id: str,
    usuario_id: str,
    dados: dict[str, str | None],
) -> PerfilFuncionario:
    """A unique (projeto, usuário) vale também para perfil apagado: reativa."""
    perfil = db.scalar(
        select(PerfilFuncionario).where(
            PerfilFuncionario.projeto_id == projeto_id,
            PerfilFuncionario.usuario_id == usuario_id,
        )
    )
    agora_ = agora()
    if perfil is None:
        perfil = PerfilFuncionario(
            id=novo_id(),
            projeto_id=projeto_id,
            usuario_id=usuario_id,
            criado_em=agora_,
            deleted_at=None,
            **dados,
        )
        db.add(perfil)
    else:
        for campo, valor in dados.items():
            setattr(perfil, campo, valor)
        perfil.deleted_at = None
    perfil.atualizado_em = agora_
    db.commit()
    return perfil


def listar_perfis(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
    *,
    limite: int | None = None,
    deslocamento: int = 0,
) -> list[PerfilFuncionario]:
    exigir_papel(db, usuario, projeto_id, {"CONSULTOR", "ORGAO"})
    ativos = membros_ativos(db, projeto_id)
    if not ativos:
        return []
    consulta = (
        select(PerfilFuncionario)
        .where(
            PerfilFuncionario.projeto_id == projeto_id,
            PerfilFuncionario.deleted_at.is_(None),
            PerfilFuncionario.usuario_id.in_(ativos),
        )
        .order_by(PerfilFuncionario.criado_em)
    )
    if limite is not None:
        consulta = consulta.limit(max(1, min(limite, 500))).offset(max(0, deslocamento))
    return list(db.scalars(consulta).all())


def contar_perfis(db: Session, usuario: Usuario, projeto_id: str) -> int:
    exigir_papel(db, usuario, projeto_id, {"CONSULTOR", "ORGAO"})
    ativos = membros_ativos(db, projeto_id)
    if not ativos:
        return 0
    total = db.scalar(
        select(func.count())
        .select_from(PerfilFuncionario)
        .where(
            PerfilFuncionario.projeto_id == projeto_id,
            PerfilFuncionario.deleted_at.is_(None),
            PerfilFuncionario.usuario_id.in_(ativos),
        )
    )
    return int(total or 0)


def arvore_hierarquica(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
) -> list[dict[str, object]]:
    """Raízes e subordinados, derivados de superior_id.

    Só entra FUNCIONARIO ativo. Superior fora desse conjunto não segura
    o nó: ele sobe à raiz com chefia_fora_do_orgao.
    """
    perfis = listar_perfis(db, usuario, projeto_id)
    ativos = membros_ativos(db, projeto_id)
    perfis = [p for p in perfis if p.usuario_id in ativos]
    por_superior: dict[str | None, list[PerfilFuncionario]] = {}
    for perfil in perfis:
        superior = perfil.superior_id if perfil.superior_id in ativos else None
        por_superior.setdefault(superior, []).append(perfil)
    ids = [p.usuario_id for p in perfis]
    pessoas = {
        u.id: u
        for u in (
            db.scalars(select(Usuario).where(Usuario.id.in_(ids))).all() if ids else []
        )
    }
    cargo_ids = [p.cargo_id for p in perfis if p.cargo_id]
    setor_ids = [p.setor_id for p in perfis if p.setor_id]
    cargos = {
        c.id: c
        for c in (
            db.scalars(
                select(Cargo).where(
                    Cargo.id.in_(cargo_ids),
                    Cargo.deleted_at.is_(None),
                )
            ).all()
            if cargo_ids
            else []
        )
    }
    setores = {
        s.id: s
        for s in (
            db.scalars(
                select(Setor).where(
                    Setor.id.in_(setor_ids),
                    Setor.deleted_at.is_(None),
                )
            ).all()
            if setor_ids
            else []
        )
    }

    def montar(perfil: PerfilFuncionario) -> dict[str, object]:
        pessoa = pessoas.get(perfil.usuario_id)
        cargo = cargos.get(perfil.cargo_id) if perfil.cargo_id else None
        setor = setores.get(perfil.setor_id) if perfil.setor_id else None
        return {
            "usuario_id": perfil.usuario_id,
            "nome": pessoa.nome if pessoa else "",
            "email": pessoa.email if pessoa else "",
            "cargo": cargo.nome if cargo else None,
            "setor": setor.nome if setor else None,
            "chefia_fora_do_orgao": bool(perfil.superior_id)
            and perfil.superior_id not in ativos,
            "subordinados": [
                montar(filho)
                for filho in por_superior.get(perfil.usuario_id, [])
            ],
        }

    if len(perfis) > 1000:
        return [
            {
                "usuario_id": raiz.usuario_id,
                "filhos_total": len(por_superior.get(raiz.usuario_id, [])),
                "truncada": True,
            }
            for raiz in por_superior.get(None, [])
        ]
    return [montar(raiz) for raiz in por_superior.get(None, [])]


def filhos_hierarquicos(
    db: Session,
    usuario: Usuario,
    projeto_id: str,
    usuario_id: str,
    *,
    limite: int = 100,
    deslocamento: int = 0,
) -> list[PerfilFuncionario]:
    exigir_papel(db, usuario, projeto_id, {"CONSULTOR", "ORGAO"})
    return list(
        db.scalars(
            select(PerfilFuncionario)
            .where(
                PerfilFuncionario.projeto_id == projeto_id,
                PerfilFuncionario.superior_id == usuario_id,
                PerfilFuncionario.deleted_at.is_(None),
            )
            .order_by(PerfilFuncionario.criado_em)
            .limit(max(1, min(limite, 100)))
            .offset(max(0, deslocamento))
        ).all()
    )
