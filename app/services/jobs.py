"""Importação, convites e exportação fora do request, em lotes."""

from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from app.models.base import agora
from app.models.tarefa import Tarefa
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth, criar_convite
from app.services.importacao import LinhaImportacao, confirmar_importacao
from app.services.projeto import listar_equipe
from app.services.tarefa import concluir_tarefa, criar_tarefa

LOTE = 200


def agendar_importacao(
    db: Session,
    dono: Usuario,
    projeto_id: str,
    linhas: list[dict],
) -> Tarefa:
    return criar_tarefa(
        db,
        dono,
        "IMPORTACAO",
        projeto_id=projeto_id,
        total=len(linhas),
    )


def agendar_convites(
    db: Session,
    dono: Usuario,
    projeto_id: str,
    convites: list[dict],
) -> Tarefa:
    return criar_tarefa(
        db,
        dono,
        "CONVITES",
        projeto_id=projeto_id,
        total=len(convites),
    )


def agendar_exportacao(db: Session, dono: Usuario, projeto_id: str) -> Tarefa:
    return criar_tarefa(db, dono, "EXPORTACAO", projeto_id=projeto_id, total=1)


def _abrir() -> Session:
    from app.core.database import SessionLocal, get_engine

    get_engine()
    if SessionLocal is None:
        raise ErroAuth(503, "Banco indisponível.")
    return SessionLocal()


def _andamento(db: Session, tarefa_id: str) -> Tarefa | None:
    linha = db.get(Tarefa, tarefa_id)
    if linha is None:
        return None
    linha.status = "EXECUTANDO"
    linha.atualizado_em = agora()
    db.commit()
    return linha


def executar_importacao(
    tarefa_id: str,
    dono_id: str,
    projeto_id: str,
    linhas: list[dict],
) -> None:
    with _abrir() as db:
        tarefa = _andamento(db, tarefa_id)
        dono = db.get(Usuario, dono_id)
        if tarefa is None or dono is None:
            return
        falhas = 0
        feito = 0
        for inicio in range(0, len(linhas), LOTE):
            fatia = [
                LinhaImportacao(
                    nome=str(item.get("nome", "")),
                    email=str(item.get("email", "")),
                    cargo=str(item.get("cargo", "")),
                    setor=str(item.get("setor", "")),
                    superior_email=str(item.get("superior_email", "")),
                    erros=[],
                )
                for item in linhas[inicio : inicio + LOTE]
            ]
            try:
                confirmar_importacao(db, dono, projeto_id, fatia)
            except ErroAuth:
                db.rollback()
                falhas += len(fatia)
            feito += len(fatia)
            tarefa = db.get(Tarefa, tarefa_id)
            if tarefa is not None:
                tarefa.feito = feito
                tarefa.falhas = falhas
                db.commit()
        tarefa = db.get(Tarefa, tarefa_id)
        if tarefa is not None:
            concluir_tarefa(db, tarefa, falhas)


def executar_convites(
    tarefa_id: str,
    dono_id: str,
    projeto_id: str,
    convites: list[dict],
) -> None:
    falhas = 0
    feito = 0
    for item in convites:
        with _abrir() as db:
            if feito == 0:
                _andamento(db, tarefa_id)
            dono = db.get(Usuario, dono_id)
            if dono is None:
                return
            try:
                criar_convite(
                    db,
                    dono,
                    str(item.get("nome", "")),
                    str(item.get("email", "")),
                    str(item.get("papel", "FUNCIONARIO")),
                    projeto_id,
                )
            except ErroAuth:
                db.rollback()
                falhas += 1
            feito += 1
            tarefa = db.get(Tarefa, tarefa_id)
            if tarefa is not None:
                tarefa.feito = feito
                tarefa.falhas = falhas
                db.commit()
    with _abrir() as db:
        tarefa = db.get(Tarefa, tarefa_id)
        if tarefa is not None:
            concluir_tarefa(db, tarefa, falhas)


def executar_exportacao(tarefa_id: str, dono_id: str, projeto_id: str) -> None:
    with _abrir() as db:
        tarefa = _andamento(db, tarefa_id)
        dono = db.get(Usuario, dono_id)
        if tarefa is None or dono is None:
            return
        try:
            equipe = listar_equipe(db, dono, projeto_id, limite=100, deslocamento=0)
        except ErroAuth as exc:
            tarefa.erro = exc.detalhe[:160]
            concluir_tarefa(db, tarefa, 1)
            return
        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";")
        escritor.writerow(["nome", "email", "papel", "situacao"])
        for pessoa in equipe:
            escritor.writerow(
                [
                    pessoa.get("nome", ""),
                    pessoa.get("email", ""),
                    pessoa.get("papel", ""),
                    pessoa.get("situacao", ""),
                ]
            )
        tarefa = db.get(Tarefa, tarefa_id)
        if tarefa is None:
            return
        tarefa.resumo = buffer.getvalue()
        tarefa.total = len(equipe)
        tarefa.feito = len(equipe)
        concluir_tarefa(db, tarefa, 0)
