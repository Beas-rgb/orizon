"""Importação de funcionários por CSV ou XLSX.

Fluxo: upload → leitura → mapeamento → validação → prévia → confirmação →
transação. Não salva parcial sem confirmação explícita.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.models.base import agora
from app.models.estrutura import Cargo, PerfilFuncionario
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.setor import Setor
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth, email_acesso

LIMITE_LINHAS = 500
LIMITE_BYTES = 2 * 1024 * 1024
COLUNAS_MINIMAS = {"nome", "email"}
COLUNAS_OPCIONAIS = {"cargo", "setor", "superior_email"}


class ImportacaoInvalida(Exception):
    pass


@dataclass(frozen=True)
class LinhaImportacao:
    nome: str
    email: str
    cargo: str
    setor: str
    superior_email: str
    erros: list[str]


@dataclass(frozen=True)
class PreviaImportacao:
    total: int
    validos: int
    invalidos: int
    setores: int
    cargos: int
    niveis: int
    duplicados: int
    superiores_inexistentes: int
    linhas: list[LinhaImportacao]


def _ler_csv(conteudo: bytes) -> list[dict[str, str]]:
    if len(conteudo) > LIMITE_BYTES:
        raise ImportacaoInvalida("Arquivo maior que 2 MB.")
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportacaoInvalida("O CSV precisa ser UTF-8.") from None
    if "<html" in texto.lower() or "<?xml" in texto.lower():
        raise ImportacaoInvalida("O conteúdo não parece CSV.")
    leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
    if leitor.fieldnames is None or len(leitor.fieldnames) < 2:
        leitor = csv.DictReader(io.StringIO(texto), delimiter=",")
    if leitor.fieldnames is None:
        raise ImportacaoInvalida("Não encontrei cabeçalho no CSV.")
    linhas = []
    for i, linha in enumerate(leitor):
        if i >= LIMITE_LINHAS:
            raise ImportacaoInvalida(f"Máximo de {LIMITE_LINHAS} linhas.")
        linhas.append({k.strip().lower(): (v or "").strip() for k, v in linha.items()})
    return linhas


def _ler_xlsx(conteudo: bytes) -> list[dict[str, str]]:
    if len(conteudo) > LIMITE_BYTES:
        raise ImportacaoInvalida("Arquivo maior que 2 MB.")
    if not conteudo[:4] == b"PK\x03\x04":
        raise ImportacaoInvalida("O conteúdo não é um XLSX válido.")
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ImportacaoInvalida("XLSX não está disponível neste ambiente.") from None
    try:
        planilha = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        aba = planilha.active
        linhas = []
        cabecalho = None
        for i, linha in enumerate(aba.iter_rows(values_only=True)):
            if i >= LIMITE_LINHAS:
                raise ImportacaoInvalida(f"Máximo de {LIMITE_LINHAS} linhas.")
            if cabecalho is None:
                cabecalho = [str(c or "").strip().lower() for c in linha]
                continue
            linhas.append(
                {
                    cabecalho[j]: str(linha[j] or "").strip()
                    for j in range(len(cabecalho))
                }
            )
        return linhas
    except Exception as exc:
        raise ImportacaoInvalida(f"Não consegui ler o XLSX: {exc}") from exc


def ler_arquivo(conteudo: bytes, nome: str) -> list[dict[str, str]]:
    """CSV ou XLSX. A extensão é só dica; o conteúdo manda."""
    if nome.lower().endswith(".csv"):
        return _ler_csv(conteudo)
    if nome.lower().endswith(".xlsx"):
        return _ler_xlsx(conteudo)
    raise ImportacaoInvalida("Envie um arquivo .csv ou .xlsx.")


def _email_valido(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def validar_linhas(
    db: Session,
    projeto: Projeto,
    linhas: list[dict[str, str]],
) -> PreviaImportacao:
    """Valida tudo antes de gravar. Não toca no banco."""
    if not linhas:
        raise ImportacaoInvalida("Nenhuma linha no arquivo.")
    if len(linhas) > LIMITE_LINHAS:
        raise ImportacaoInvalida(f"Máximo de {LIMITE_LINHAS} linhas.")

    setores_existentes = {
        s.nome.strip().lower(): s.id
        for s in db.scalars(
            select(Setor).where(
                Setor.projeto_id == projeto.id,
                Setor.deleted_at.is_(None),
            )
        ).all()
    }
    cargos_existentes = {
        c.nome.strip().lower(): c.id
        for c in db.scalars(
            select(Cargo).where(
                Cargo.projeto_id == projeto.id,
                Cargo.deleted_at.is_(None),
            )
        ).all()
    }
    emails_no_projeto = {
        u.email
        for u in db.scalars(
            select(Usuario)
            .join(ProjetoUsuario, ProjetoUsuario.usuario_id == Usuario.id)
            .where(
                ProjetoUsuario.projeto_id == projeto.id,
                ProjetoUsuario.papel == "FUNCIONARIO",
                Usuario.deleted_at.is_(None),
            )
        ).all()
    }

    vistos: set[str] = set()
    linhas_validadas: list[LinhaImportacao] = []
    setores_novos: set[str] = set()
    cargos_novos: set[str] = set()
    superiores_inexistentes = 0
    duplicados = 0

    for i, linha in enumerate(linhas, start=2):
        nome = linha.get("nome", "").strip()
        email = email_acesso(linha.get("email", ""))
        cargo = linha.get("cargo", "").strip()
        setor = linha.get("setor", "").strip()
        superior_email = email_acesso(linha.get("superior_email", ""))
        erros: list[str] = []

        if not nome:
            erros.append("nome ausente")
        if not email:
            erros.append("email ausente")
        elif not _email_valido(email):
            erros.append("email inválido")
        elif email in vistos:
            erros.append("email duplicado no arquivo")
            duplicados += 1
        elif email in emails_no_projeto:
            erros.append("email já existe neste projeto")
        if setor and setor.lower() not in setores_existentes:
            setores_novos.add(setor.lower())
        if cargo and cargo.lower() not in cargos_existentes:
            cargos_novos.add(cargo.lower())
        if (
            superior_email
            and superior_email not in vistos
            and superior_email not in emails_no_projeto
        ):
            superiores_inexistentes += 1
            erros.append("superior não encontrado")

        vistos.add(email)
        linhas_validadas.append(
            LinhaImportacao(
                nome=nome,
                email=email,
                cargo=cargo,
                setor=setor,
                superior_email=superior_email,
                erros=erros,
            )
        )

    # Ciclo: A→B→A
    mapa_superior = {
        linha.email: linha.superior_email
        for linha in linhas_validadas
        if linha.superior_email
    }
    for email in mapa_superior:
        atual = email
        vistos_ciclo = set()
        while atual in mapa_superior:
            if atual in vistos_ciclo:
                for linha in linhas_validadas:
                    if linha.email == email:
                        linha.erros.append("hierarquia em ciclo")
                break
            vistos_ciclo.add(atual)
            atual = mapa_superior[atual]

    validos = sum(1 for linha in linhas_validadas if not linha.erros)
    invalidos = len(linhas_validadas) - validos
    niveis = _niveis_hierarquia(linhas_validadas)

    return PreviaImportacao(
        total=len(linhas_validadas),
        validos=validos,
        invalidos=invalidos,
        setores=len(setores_existentes) + len(setores_novos),
        cargos=len(cargos_existentes) + len(cargos_novos),
        niveis=niveis,
        duplicados=duplicados,
        superiores_inexistentes=superiores_inexistentes,
        linhas=linhas_validadas,
    )


def _niveis_hierarquia(linhas: list[LinhaImportacao]) -> int:
    mapa = {
        linha.email: linha.superior_email
        for linha in linhas
        if linha.superior_email
    }
    if not mapa:
        return 1
    niveis = 1
    for email in mapa:
        profundidade = 1
        atual = email
        vistos = set()
        while atual in mapa and atual not in vistos:
            vistos.add(atual)
            atual = mapa[atual]
            profundidade += 1
        niveis = max(niveis, profundidade)
    return niveis


def confirmar_importacao(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    linhas: list[LinhaImportacao],
) -> dict[str, int]:
    """Grava só as linhas válidas. Revalida. O cliente não é fonte dos erros."""
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    projeto = db.get(Projeto, projeto_id)
    if (
        projeto is None
        or projeto.deleted_at is not None
        or projeto.consultor_id != consultor.id
    ):
        raise ErroAuth(404, "Projeto não encontrado.")

    enviadas = len(linhas)
    brutas = [
        {
            "nome": linha.nome,
            "email": linha.email,
            "cargo": linha.cargo,
            "setor": linha.setor,
            "superior_email": linha.superior_email,
        }
        for linha in linhas
    ]
    try:
        previa = validar_linhas(db, projeto, brutas)
    except ImportacaoInvalida as exc:
        raise ErroAuth(422, str(exc)) from None
    linhas = [linha for linha in previa.linhas if not linha.erros]

    setores = {
        s.nome.strip().lower(): s
        for s in db.scalars(
            select(Setor).where(
                Setor.projeto_id == projeto_id,
                Setor.deleted_at.is_(None),
            )
        ).all()
    }
    cargos = {
        c.nome.strip().lower(): c
        for c in db.scalars(
            select(Cargo).where(
                Cargo.projeto_id == projeto_id,
                Cargo.deleted_at.is_(None),
            )
        ).all()
    }

    criados = 0
    agora_ = agora()
    emails = {linha.email for linha in linhas if linha.email}
    emails.update(linha.superior_email for linha in linhas if linha.superior_email)
    usuarios = {}
    if emails:
        usuarios = {
            pessoa.email: pessoa
            for pessoa in db.scalars(
                select(Usuario).where(
                    Usuario.email.in_(emails),
                    Usuario.deleted_at.is_(None),
                )
            ).all()
        }
    ids = [pessoa.id for pessoa in usuarios.values()]
    vinculos = set()
    perfis = {}
    if ids:
        vinculos = set(
            db.scalars(
                select(ProjetoUsuario.usuario_id).where(
                    ProjetoUsuario.projeto_id == projeto_id,
                    ProjetoUsuario.usuario_id.in_(ids),
                )
            ).all()
        )
        perfis = {
            perfil.usuario_id: perfil
            for perfil in db.scalars(
                select(PerfilFuncionario).where(
                    PerfilFuncionario.projeto_id == projeto_id,
                    PerfilFuncionario.usuario_id.in_(ids),
                    PerfilFuncionario.deleted_at.is_(None),
                )
            ).all()
        }
    for linha in linhas:
        if linha.erros:
            continue
        setor = None
        if linha.setor:
            chave = linha.setor.strip().lower()
            setor = setores.get(chave)
            if setor is None:
                setor = Setor(
                    id=novo_id(),
                    projeto_id=projeto_id,
                    nome=linha.setor.strip()[:120],
                    criado_em=agora_,
                    atualizado_em=agora_,
                    deleted_at=None,
                )
                db.add(setor)
                db.flush()
                setores[chave] = setor
        cargo = None
        if linha.cargo:
            chave = linha.cargo.strip().lower()
            cargo = cargos.get(chave)
            if cargo is None:
                cargo = Cargo(
                    id=novo_id(),
                    projeto_id=projeto_id,
                    nome=linha.cargo.strip()[:120],
                    criado_em=agora_,
                    atualizado_em=agora_,
                    deleted_at=None,
                )
                db.add(cargo)
                db.flush()
                cargos[chave] = cargo

        usuario = usuarios.get(linha.email)
        if usuario is None:
            usuario = Usuario(
                id=novo_id(),
                nome=linha.nome.strip()[:160],
                email=linha.email,
                senha_hash=None,
                papel="FUNCIONARIO",
                ativo=False,
                tentativas_falhas=0,
                criado_em=agora_,
                atualizado_em=agora_,
                deleted_at=None,
            )
            db.add(usuario)
            db.flush()
            usuarios[usuario.email] = usuario
        if usuario.id not in vinculos:
            db.add(
                ProjetoUsuario(
                    id=novo_id(),
                    projeto_id=projeto_id,
                    usuario_id=usuario.id,
                    papel="FUNCIONARIO",
                )
            )
            vinculos.add(usuario.id)
        superior = usuarios.get(linha.superior_email) if linha.superior_email else None
        perfil = perfis.get(usuario.id)
        if perfil is None:
            perfil = PerfilFuncionario(
                id=novo_id(),
                projeto_id=projeto_id,
                usuario_id=usuario.id,
                setor_id=setor.id if setor else None,
                cargo_id=cargo.id if cargo else None,
                superior_id=superior.id if superior else None,
                criado_em=agora_,
                atualizado_em=agora_,
                deleted_at=None,
            )
            db.add(perfil)
            perfis[usuario.id] = perfil
        else:
            perfil.setor_id = setor.id if setor else None
            perfil.cargo_id = cargo.id if cargo else None
            perfil.superior_id = superior.id if superior else None
            perfil.atualizado_em = agora_
        criados += 1

    db.commit()
    return {"criados": criados, "total": enviadas}
