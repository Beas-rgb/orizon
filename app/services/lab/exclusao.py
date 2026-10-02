"""Exclusão completa e verificada do cenário. Só apaga SINTETICO da subárvore."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.base import agora
from app.models.configuracao import ConfiguracaoProjeto
from app.models.desempenho import (
    AvaliacaoRelacionamento,
    AvaliacaoResposta,
    CicloAvaliacao,
)
from app.models.estrutura import Cargo, PerfilFuncionario
from app.models.lab import CenarioLab
from app.models.organizacao import Organizacao
from app.models.pesquisa import (
    OpcaoResposta,
    Pergunta,
    Pesquisa,
    PesquisaParticipante,
    Resposta,
    TokenResposta,
)
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.sessao import Sessao
from app.models.setor import Setor
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth
from app.services.lab.cenario import _marcar, obter_cenario

LOTE = 500


def solicitar_exclusao(
    db: Session,
    dono: Usuario,
    cenario_id: str,
    confirmo: str,
) -> CenarioLab:
    cenario = obter_cenario(db, dono, cenario_id)
    if confirmo.strip() != cenario.nome:
        raise ErroAuth(422, "Digite o nome do cenário para confirmar.")
    if cenario.status == "EXCLUINDO":
        return cenario
    cenario.status = "EXCLUINDO"
    cenario.progresso = 0
    cenario.atualizado_em = agora()
    db.commit()
    db.refresh(cenario)
    return cenario


def _apagar_ids(db: Session, modelo, coluna, ids: list[str]) -> int:
    if not ids:
        return 0
    total = 0
    for i in range(0, len(ids), LOTE):
        fatia = ids[i : i + LOTE]
        result = db.execute(delete(modelo).where(coluna.in_(fatia)))
        total += result.rowcount or 0
        db.commit()
    return total


def _ids_pesquisa(db: Session, projeto_id: str) -> list[str]:
    return list(
        db.scalars(
            select(Pesquisa.id).where(Pesquisa.projeto_id == projeto_id)
        ).all()
    )


def _ids_sinteticos(db: Session, cenario_id: str) -> list[str]:
    dominio = f".{cenario_id[:8]}@sintetico.invalid"
    return list(
        db.scalars(
            select(Usuario.id).where(
                Usuario.tipo_conta == "SINTETICO",
                Usuario.email.like(f"%{dominio}"),
            )
        ).all()
    )


def executar_exclusao(cenario_id: str, dono_id: str) -> None:
    from app.core.database import SessionLocal, get_engine

    get_engine()
    if SessionLocal is None:
        return
    with SessionLocal() as db:
        cenario = db.get(CenarioLab, cenario_id)
        if cenario is None:
            return
        if cenario.dono_id != dono_id:
            return
        if cenario.status != "EXCLUINDO":
            return
        try:
            projeto_id = cenario.projeto_id
            org_id = None
            if projeto_id:
                projeto = db.get(Projeto, projeto_id)
                if projeto is not None and projeto.consultor_id == dono_id:
                    org_id = projeto.organizacao_id
                    _apagar_subarvore(db, cenario_id, projeto_id, org_id, dono_id)
                else:
                    # Projeto estranho: não apaga nada além do registro do cenário
                    pass
            # Verifica resíduos sintéticos deste cenário
            restam = db.scalar(
                select(func.count())
                .select_from(Usuario)
                .where(
                    Usuario.tipo_conta == "SINTETICO",
                    Usuario.email.like(f"%.{cenario_id[:8]}@sintetico.invalid"),
                )
            )
            if restam and restam > 0:
                _marcar(
                    db,
                    cenario_id,
                    0,
                    status="ERRO",
                    erro=f"Restaram {restam} sintéticos.",
                )
                return
            if projeto_id:
                ainda = db.get(Projeto, projeto_id)
                if ainda is not None:
                    _marcar(
                        db,
                        cenario_id,
                        0,
                        status="ERRO",
                        erro="Projeto não foi removido.",
                    )
                    return
            db.execute(delete(CenarioLab).where(CenarioLab.id == cenario_id))
            db.commit()
        except Exception as exc:
            _marcar(
                db,
                cenario_id,
                0,
                status="ERRO",
                erro=type(exc).__name__[:500],
            )


def _apagar_subarvore(
    db: Session,
    cenario_id: str,
    projeto_id: str,
    org_id: str,
    dono_id: str,
) -> None:
    pesquisas = _ids_pesquisa(db, projeto_id)
    _marcar(db, cenario_id, 10)

    if pesquisas:
        perguntas = list(
            db.scalars(
                select(Pergunta.id).where(Pergunta.pesquisa_id.in_(pesquisas))
            ).all()
        )
        tokens = list(
            db.scalars(
                select(TokenResposta.id).where(
                    TokenResposta.pesquisa_id.in_(pesquisas)
                )
            ).all()
        )
        if tokens:
            _apagar_ids(db, Resposta, Resposta.token_id, tokens)
        _apagar_ids(
            db,
            PesquisaParticipante,
            PesquisaParticipante.pesquisa_id,
            pesquisas,
        )
        _apagar_ids(db, TokenResposta, TokenResposta.pesquisa_id, pesquisas)
        if perguntas:
            _apagar_ids(db, OpcaoResposta, OpcaoResposta.pergunta_id, perguntas)
            _apagar_ids(db, Pergunta, Pergunta.id, perguntas)
        _marcar(db, cenario_id, 40)

        ciclos = list(
            db.scalars(
                select(CicloAvaliacao.id).where(
                    CicloAvaliacao.projeto_id == projeto_id
                )
            ).all()
        )
        if ciclos:
            rels = list(
                db.scalars(
                    select(AvaliacaoRelacionamento.id).where(
                        AvaliacaoRelacionamento.ciclo_id.in_(ciclos)
                    )
                ).all()
            )
            if rels:
                _apagar_ids(
                    db,
                    AvaliacaoResposta,
                    AvaliacaoResposta.relacionamento_id,
                    rels,
                )
                _apagar_ids(
                    db,
                    AvaliacaoRelacionamento,
                    AvaliacaoRelacionamento.id,
                    rels,
                )
            _apagar_ids(db, CicloAvaliacao, CicloAvaliacao.id, ciclos)
        _apagar_ids(db, Pesquisa, Pesquisa.id, pesquisas)

    _marcar(db, cenario_id, 55)
    _apagar_ids(
        db,
        PerfilFuncionario,
        PerfilFuncionario.projeto_id,
        [projeto_id],
    )
    # Vínculos do projeto, exceto o dono TESTE (ele não é sintético)
    sinteticos = _ids_sinteticos(db, cenario_id)
    if sinteticos:
        db.execute(
            delete(ProjetoUsuario).where(
                ProjetoUsuario.projeto_id == projeto_id,
                ProjetoUsuario.usuario_id.in_(sinteticos),
            )
        )
        db.commit()
        _apagar_ids(db, Sessao, Sessao.usuario_id, sinteticos)
    db.execute(
        delete(ProjetoUsuario).where(ProjetoUsuario.projeto_id == projeto_id)
    )
    db.commit()
    _apagar_ids(db, Setor, Setor.projeto_id, [projeto_id])
    _apagar_ids(db, Cargo, Cargo.projeto_id, [projeto_id])
    db.execute(
        delete(ConfiguracaoProjeto).where(
            ConfiguracaoProjeto.projeto_id == projeto_id
        )
    )
    db.commit()
    _marcar(db, cenario_id, 75)

    # Só apaga usuários SINTETICO deste cenário
    if sinteticos:
        db.execute(
            delete(Usuario).where(
                Usuario.id.in_(sinteticos),
                Usuario.tipo_conta == "SINTETICO",
                Usuario.email.like(f"%.{cenario_id[:8]}@sintetico.invalid"),
            )
        )
        db.commit()

    projeto = db.get(Projeto, projeto_id)
    if projeto is not None and projeto.consultor_id == dono_id:
        db.delete(projeto)
        db.commit()
    org = db.get(Organizacao, org_id)
    if org is not None and org.razao_social.startswith("LAB "):
        # Só remove se nenhum outro projeto apontar
        outros = db.scalar(
            select(func.count())
            .select_from(Projeto)
            .where(Projeto.organizacao_id == org_id)
        )
        if not outros:
            db.delete(org)
            db.commit()
    _marcar(db, cenario_id, 95)
