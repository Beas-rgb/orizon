"""Painel agregado de resultados da pesquisa."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.autorizacao import papel_no_projeto
from app.models.pesquisa import OpcaoResposta, Pergunta, Resposta
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth

from app.services.pesquisa.comum import K_ANONIMATO, TIPOS_ANONIMOS, _pesquisa_viva


def painel(db: Session, usuario: Usuario, pesquisa_id: str) -> list[dict]:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    papel = papel_no_projeto(db, usuario, pesquisa.projeto_id)
    if papel not in {"CONSULTOR", "ORGAO"}:
        raise ErroAuth(404, "Pesquisa não encontrada.")
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
    if not perguntas:
        return []
    ids = [p.id for p in perguntas]
    totais = {
        row.pergunta_id: int(row.total)
        for row in db.execute(
            select(
                Resposta.pergunta_id,
                func.count(func.distinct(Resposta.token_id)).label("total"),
            )
            .where(Resposta.pergunta_id.in_(ids))
            .group_by(Resposta.pergunta_id)
        ).all()
    }
    medias = {
        row.pergunta_id: float(row.media)
        for row in db.execute(
            select(
                Resposta.pergunta_id,
                func.avg(Resposta.valor_numerico).label("media"),
            )
            .where(
                Resposta.pergunta_id.in_(ids),
                Resposta.valor_numerico.is_not(None),
            )
            .group_by(Resposta.pergunta_id)
        ).all()
    }
    contagens_por_pergunta: dict[str, list[dict]] = {pid: [] for pid in ids}
    opcoes = list(
        db.scalars(
            select(OpcaoResposta)
            .where(OpcaoResposta.pergunta_id.in_(ids))
            .order_by(OpcaoResposta.ordem)
        ).all()
    )
    if opcoes:
        opcao_ids = [o.id for o in opcoes]
        qtd_por_opcao = {
            row.opcao_id: int(row.total)
            for row in db.execute(
                select(
                    Resposta.opcao_id,
                    func.count(Resposta.id).label("total"),
                )
                .where(Resposta.opcao_id.in_(opcao_ids))
                .group_by(Resposta.opcao_id)
            ).all()
        }
        for opcao in opcoes:
            contagens_por_pergunta[opcao.pergunta_id].append(
                {
                    "opcao_id": opcao.id,
                    "texto": opcao.texto,
                    "total": qtd_por_opcao.get(opcao.id, 0),
                }
            )
    saida = []
    for pergunta in perguntas:
        total = totais.get(pergunta.id, 0)
        suprimido = pesquisa.tipo in TIPOS_ANONIMOS and total < K_ANONIMATO
        media = None
        contagem_opcoes = None
        if not suprimido:
            media = medias.get(pergunta.id)
            if pergunta.tipo in {"CHECKBOX", "MULTIPLA_ESCOLHA", "SIM_NAO"}:
                contagem_opcoes = contagens_por_pergunta.get(pergunta.id, [])
        saida.append(
            {
                "pergunta_id": pergunta.id,
                "texto": pergunta.texto,
                "tipo": pergunta.tipo,
                "respostas": total,
                "media": media,
                "contagem_opcoes": contagem_opcoes,
                "suprimido": suprimido,
            }
        )
    return saida
