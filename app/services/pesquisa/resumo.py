"""Resumo do trabalho com K aplicado no servidor. Sem N baixo em CLIMA."""

from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.services.pesquisa.crud import listar_pesquisas
from app.services.pesquisa.painel import painel
from app.services.projeto import obter_projeto


def resumo_do_projeto(db: Session, usuario: Usuario, projeto_id: str) -> dict:
    obter_projeto(db, usuario, projeto_id)
    pesquisas = listar_pesquisas(db, usuario, projeto_id)
    itens = []
    for pesquisa in pesquisas:
        if pesquisa.status not in {"PUBLICADA", "ENCERRADA"}:
            continue
        itens.append(
            {
                "pesquisa_id": pesquisa.id,
                "titulo": pesquisa.titulo,
                "tipo": pesquisa.tipo,
                "status": pesquisa.status,
                "perguntas": painel(db, usuario, pesquisa.id),
            }
        )
    return {"projeto_id": projeto_id, "pesquisas": itens}
