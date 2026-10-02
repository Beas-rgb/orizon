"""Respostas sintéticas pelo caminho real de registro."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import agora
from app.models.lab import CenarioLab
from app.models.pesquisa import OpcaoResposta, Pergunta, Pesquisa, PesquisaParticipante
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth
from app.services.lab.cenario import _marcar, obter_cenario
from app.services.lab.geradores import PERFIS, rng_de
from app.services.pesquisa.resposta import registrar_respostas_da_pesquisa

LOTE = 100


def _valor_para(
    rng,
    pergunta: Pergunta,
    opcoes: list[OpcaoResposta],
    perfil: str,
) -> dict:
    if pergunta.tipo == "NOTA_5":
        if perfil == "POSITIVO":
            nota = rng.choice([4, 5])
        elif perfil == "NEGATIVO":
            nota = rng.choice([1, 2])
        elif perfil == "NEUTRO":
            nota = 3
        else:
            nota = rng.randint(1, 5)
        return {"pergunta_id": pergunta.id, "valor_numerico": nota}
    if pergunta.tipo == "NOTA_10":
        if perfil == "POSITIVO":
            nota = rng.randint(8, 10)
        elif perfil == "NEGATIVO":
            nota = rng.randint(1, 3)
        elif perfil == "NEUTRO":
            nota = 5
        else:
            nota = rng.randint(1, 10)
        return {"pergunta_id": pergunta.id, "valor_numerico": nota}
    if pergunta.tipo == "TEXTO_LIVRE":
        return {
            "pergunta_id": pergunta.id,
            "valor_texto": f"texto lab {rng.randint(1, 999)}",
        }
    opcoes = sorted(opcoes, key=lambda o: o.ordem)
    if not opcoes:
        raise ErroAuth(422, "Pergunta sem opções.")
    if pergunta.tipo == "SIM_NAO":
        sim = opcoes[0].id
        nao = opcoes[1].id if len(opcoes) > 1 else opcoes[0].id
        if perfil == "POSITIVO":
            escolhido = sim if rng.random() < 0.8 else nao
        elif perfil == "NEGATIVO":
            escolhido = sim if rng.random() < 0.2 else nao
        elif perfil == "NEUTRO":
            escolhido = sim if rng.random() < 0.5 else nao
        else:
            escolhido = rng.choice([sim, nao])
        return {"pergunta_id": pergunta.id, "opcao_id": escolhido}
    if pergunta.tipo == "MULTIPLA_ESCOLHA":
        return {
            "pergunta_id": pergunta.id,
            "opcao_id": rng.choice(opcoes).id,
        }
    # CHECKBOX: subconjunto não vazio
    qtd = rng.randint(1, len(opcoes))
    escolhidas = rng.sample([o.id for o in opcoes], qtd)
    return {"pergunta_id": pergunta.id, "opcao_ids": escolhidas}


def _pesquisa_do_projeto(db: Session, projeto_id: str) -> Pesquisa:
    pesquisa = db.scalar(
        select(Pesquisa)
        .where(
            Pesquisa.projeto_id == projeto_id,
            Pesquisa.deleted_at.is_(None),
            Pesquisa.status == "PUBLICADA",
        )
        .order_by(Pesquisa.criado_em.desc())
    )
    if pesquisa is None:
        raise ErroAuth(404, "Pesquisa do cenário não encontrada.")
    return pesquisa


def solicitar_respostas(
    db: Session,
    dono: Usuario,
    cenario_id: str,
    perfil: str,
    taxa: float,
    seed: int | None,
) -> CenarioLab:
    cenario = obter_cenario(db, dono, cenario_id)
    if cenario.status != "PRONTO":
        raise ErroAuth(409, "Cenário ainda não está pronto.")
    if perfil not in PERFIS:
        raise ErroAuth(422, "Perfil inválido.")
    if taxa < 0 or taxa > 1:
        raise ErroAuth(422, "Taxa inválida.")
    cenario.perfil = perfil
    if seed is not None:
        cenario.seed = seed
    cenario.status = "CRIANDO"
    cenario.progresso = 0
    cenario.atualizado_em = agora()
    db.commit()
    db.refresh(cenario)
    return cenario


def executar_respostas(
    cenario_id: str,
    perfil: str,
    taxa: float,
    seed: int,
) -> None:
    from app.core.database import SessionLocal, get_engine

    get_engine()
    if SessionLocal is None:
        return
    with SessionLocal() as db:
        cenario = db.get(CenarioLab, cenario_id)
        if cenario is None or cenario.projeto_id is None:
            return
        try:
            pesquisa = _pesquisa_do_projeto(db, cenario.projeto_id)
            perguntas = list(
                db.scalars(
                    select(Pergunta)
                    .where(
                        Pergunta.pesquisa_id == pesquisa.id,
                        Pergunta.deleted_at.is_(None),
                    )
                    .order_by(Pergunta.ordem)
                ).all()
            )
            ids_perg = [p.id for p in perguntas]
            opcoes_por = {pid: [] for pid in ids_perg}
            if ids_perg:
                for opcao in db.scalars(
                    select(OpcaoResposta).where(
                        OpcaoResposta.pergunta_id.in_(ids_perg)
                    )
                ).all():
                    opcoes_por[opcao.pergunta_id].append(opcao)
            participantes = list(
                db.scalars(
                    select(PesquisaParticipante).where(
                        PesquisaParticipante.pesquisa_id == pesquisa.id,
                        PesquisaParticipante.deleted_at.is_(None),
                        PesquisaParticipante.status != "RESPONDIDA",
                    )
                ).all()
            )
            rng = rng_de(seed, f"resp:{cenario_id}")
            escolhidos = [p for p in participantes if rng.random() <= taxa]
            total = len(escolhidos) or 1
            for i, part in enumerate(escolhidos):
                usuario = db.get(Usuario, part.usuario_id)
                if usuario is None or usuario.tipo_conta != "SINTETICO":
                    continue
                itens = [
                    _valor_para(
                        rng_de(seed, f"{usuario.id}:{perg.id}"),
                        perg,
                        opcoes_por.get(perg.id, []),
                        perfil,
                    )
                    for perg in perguntas
                ]
                registrar_respostas_da_pesquisa(
                    db,
                    pesquisa.id,
                    itens,
                    usuario,
                    ip=None,
                )
                if i % LOTE == 0:
                    _marcar(
                        db,
                        cenario_id,
                        min(99, int(100 * (i + 1) / total)),
                    )
            _marcar(db, cenario_id, 100, status="PRONTO", erro=None)
        except ErroAuth as exc:
            _marcar(
                db,
                cenario_id,
                0,
                status="ERRO",
                erro=str(exc.detalhe)[:500],
            )
        except Exception as exc:
            _marcar(
                db,
                cenario_id,
                0,
                status="ERRO",
                erro=type(exc).__name__[:500],
            )
