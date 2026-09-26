"""Motor da avaliação de desempenho: ciclo, relações e cálculo.

Não toca em CLIMA. TIPOS_ANONIMOS continua {"CLIMA"}.
"""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.autorizacao import exigir_papel, papel_no_projeto
from app.core.tokens import novo_id
from app.models.base import agora
from app.models.desempenho import (
    AvaliacaoRelacionamento,
    AvaliacaoResposta,
    CicloAvaliacao,
)
from app.models.estrutura import PerfilFuncionario
from app.models.pesquisa import Pergunta, Pesquisa
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.usuario import Usuario
from app.services.auditoria import registrar as _auditar
from app.services.identidade import ErroAuth

ESCOPOS = {"ORGANIZACAO", "SETOR", "CARGO", "MANUAL"}
TIPOS_RELACAO = {"AUTO", "SUPERIOR", "SUBORDINADO"}
PESOS_PADRAO = {"AUTO": 1.0, "SUPERIOR": 2.0, "SUBORDINADO": 1.0}


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


def _validar_configuracao(config: str | None) -> str | None:
    """JSON estruturado. Nunca código do usuário."""
    if config is None:
        return None
    try:
        dados = json.loads(config)
    except json.JSONDecodeError:
        raise ErroAuth(422, "Configuração inválida. Use JSON.") from None
    if not isinstance(dados, dict):
        raise ErroAuth(422, "Configuração deve ser um objeto JSON.")
    proibidas = {"eval", "exec", "import", "__", "sql", "python", "javascript"}
    for chave in dados:
        if any(p in chave.lower() for p in proibidas):
            raise ErroAuth(422, "Configuração não pode conter código.")
    if "pesos" in dados:
        pesos = dados["pesos"]
        if not isinstance(pesos, dict):
            raise ErroAuth(422, "Pesos devem ser um objeto.")
        for perspectiva, peso in pesos.items():
            if perspectiva not in TIPOS_RELACAO:
                raise ErroAuth(422, f"Perspectiva inválida: {perspectiva}.")
            if not isinstance(peso, (int, float)) or peso < 0:
                raise ErroAuth(422, "Peso deve ser número positivo.")
    if "ordem" in dados:
        ordem = dados["ordem"]
        if not isinstance(ordem, list):
            raise ErroAuth(422, "Ordem deve ser uma lista.")
        for item in ordem:
            if item not in TIPOS_RELACAO:
                raise ErroAuth(422, f"Perspectiva inválida na ordem: {item}.")
    return json.dumps(dados, ensure_ascii=False, sort_keys=True)


def criar_ciclo(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    nome: str,
    *,
    inicio_em: datetime | None = None,
    fim_em: datetime | None = None,
    escopo: str = "ORGANIZACAO",
    configuracao: str | None = None,
) -> CicloAvaliacao:
    _projeto_da_consultora(db, consultor, projeto_id)
    if escopo not in ESCOPOS:
        raise ErroAuth(422, "Escopo inválido.")
    if len(nome.strip()) < 2:
        raise ErroAuth(422, "Informe o nome do ciclo.")
    agora_ = agora()
    ciclo = CicloAvaliacao(
        id=novo_id(),
        projeto_id=projeto_id,
        nome=nome.strip()[:200],
        inicio_em=inicio_em,
        fim_em=fim_em,
        escopo=escopo,
        configuracao=_validar_configuracao(configuracao),
        status="RASCUNHO",
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )
    db.add(ciclo)
    _auditar(db, "CICLO_CRIADO", consultor.id)
    db.commit()
    return ciclo


def atualizar_ciclo(
    db: Session,
    consultor: Usuario,
    ciclo_id: str,
    *,
    nome: str | None = None,
    escopo: str | None = None,
    configuracao: str | None = None,
) -> CicloAvaliacao:
    """Altera rascunho: nome, escopo ou pesos. Publicado não muda."""
    ciclo = db.get(CicloAvaliacao, ciclo_id)
    if ciclo is None or ciclo.deleted_at is not None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    _projeto_da_consultora(db, consultor, ciclo.projeto_id)
    if ciclo.status != "RASCUNHO":
        raise ErroAuth(422, "Só rascunho pode ser alterado.")
    if nome is None and escopo is None and configuracao is None:
        raise ErroAuth(422, "Nada para atualizar.")
    if nome is not None:
        if len(nome.strip()) < 2:
            raise ErroAuth(422, "Informe o nome do ciclo.")
        ciclo.nome = nome.strip()[:200]
    if escopo is not None:
        if escopo not in ESCOPOS:
            raise ErroAuth(422, "Escopo inválido.")
        ciclo.escopo = escopo
    if configuracao is not None:
        ciclo.configuracao = _validar_configuracao(configuracao)
    ciclo.atualizado_em = agora()
    _auditar(db, "CICLO_ATUALIZADO", consultor.id)
    db.commit()
    return ciclo


def listar_ciclos(
    db: Session, usuario: Usuario, projeto_id: str
) -> list[CicloAvaliacao]:
    exigir_papel(db, usuario, projeto_id, {"CONSULTOR", "ORGAO"})
    return list(
        db.scalars(
            select(CicloAvaliacao)
            .where(
                CicloAvaliacao.projeto_id == projeto_id,
                CicloAvaliacao.deleted_at.is_(None),
            )
            .order_by(CicloAvaliacao.criado_em.desc())
        ).all()
    )


def _funcionarios_do_projeto(db: Session, projeto_id: str) -> list[Usuario]:
    return list(
        db.scalars(
            select(Usuario)
            .join(ProjetoUsuario, ProjetoUsuario.usuario_id == Usuario.id)
            .where(
                ProjetoUsuario.projeto_id == projeto_id,
                ProjetoUsuario.papel == "FUNCIONARIO",
                Usuario.deleted_at.is_(None),
                Usuario.ativo.is_(True),
            )
        ).all()
    )


def gerar_relacoes(
    db: Session,
    consultor: Usuario,
    ciclo_id: str,
) -> dict[str, int]:
    """Gera AUTO, SUPERIOR e SUBORDINADO a partir da hierarquia.

    Idempotente: a unique impede duplicata. Sem superior, não cria SUPERIOR.
    Sem subordinado, não cria SUBORDINADO.
    """
    ciclo = db.get(CicloAvaliacao, ciclo_id)
    if ciclo is None or ciclo.deleted_at is not None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    _projeto_da_consultora(db, consultor, ciclo.projeto_id)
    if ciclo.status != "RASCUNHO":
        raise ErroAuth(422, "Só rascunho pode gerar relações.")

    funcionarios = _funcionarios_do_projeto(db, ciclo.projeto_id)
    perfis = {
        p.usuario_id: p
        for p in db.scalars(
            select(PerfilFuncionario).where(
                PerfilFuncionario.projeto_id == ciclo.projeto_id,
                PerfilFuncionario.deleted_at.is_(None),
            )
        ).all()
    }
    subordinados: dict[str, list[str]] = {}
    for perfil in perfis.values():
        if perfil.superior_id:
            subordinados.setdefault(perfil.superior_id, []).append(perfil.usuario_id)

    agora_ = agora()
    criados = 0
    for funcionario in funcionarios:
        perfil = perfis.get(funcionario.id)
        # AUTO: sempre.
        _criar_relacao(
            db,
            ciclo.id,
            funcionario.id,
            funcionario.id,
            "AUTO",
            PESOS_PADRAO["AUTO"],
            agora_,
        )
        criados += 1
        # SUPERIOR: só se houver superior.
        if perfil and perfil.superior_id:
            _criar_relacao(
                db,
                ciclo.id,
                perfil.superior_id,
                funcionario.id,
                "SUPERIOR",
                PESOS_PADRAO["SUPERIOR"],
                agora_,
            )
            criados += 1
        # SUBORDINADO: só se houver subordinados.
        for subordinado_id in subordinados.get(funcionario.id, []):
            _criar_relacao(
                db,
                ciclo.id,
                subordinado_id,
                funcionario.id,
                "SUBORDINADO",
                PESOS_PADRAO["SUBORDINADO"],
                agora_,
            )
            criados += 1
    _auditar(db, "RELACOES_GERADAS", consultor.id)
    db.commit()
    return {"criados": criados, "funcionarios": len(funcionarios)}


def _criar_relacao(
    db: Session,
    ciclo_id: str,
    avaliador_id: str,
    avaliado_id: str,
    tipo: str,
    peso: float,
    agora_: datetime,
) -> None:
    """Cria se não existir. A unique impede duplicata."""
    ja = db.scalar(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo_id,
            AvaliacaoRelacionamento.avaliador_id == avaliador_id,
            AvaliacaoRelacionamento.avaliado_id == avaliado_id,
            AvaliacaoRelacionamento.tipo_relacao == tipo,
            AvaliacaoRelacionamento.deleted_at.is_(None),
        )
    )
    if ja is not None:
        return
    db.add(
        AvaliacaoRelacionamento(
            id=novo_id(),
            ciclo_id=ciclo_id,
            avaliador_id=avaliador_id,
            avaliado_id=avaliado_id,
            tipo_relacao=tipo,
            peso=peso,
            status="PENDENTE",
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
    )


def listar_relacoes(
    db: Session,
    usuario: Usuario,
    ciclo_id: str,
) -> list[AvaliacaoRelacionamento]:
    ciclo = db.get(CicloAvaliacao, ciclo_id)
    if ciclo is None or ciclo.deleted_at is not None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    exigir_papel(db, usuario, ciclo.projeto_id, {"CONSULTOR", "ORGAO"})
    return list(
        db.scalars(
            select(AvaliacaoRelacionamento)
            .where(
                AvaliacaoRelacionamento.ciclo_id == ciclo_id,
                AvaliacaoRelacionamento.deleted_at.is_(None),
            )
            .order_by(AvaliacaoRelacionamento.criado_em)
        ).all()
    )


def relacao_do_avaliador(
    db: Session,
    usuario: Usuario,
    ciclo_id: str,
    avaliado_id: str,
) -> AvaliacaoRelacionamento:
    """O usuário autenticado só responde pela relação que existe."""
    ciclo = db.get(CicloAvaliacao, ciclo_id)
    if ciclo is None or ciclo.deleted_at is not None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    if papel_no_projeto(db, usuario, ciclo.projeto_id) is None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    relacao = db.scalar(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo_id,
            AvaliacaoRelacionamento.avaliador_id == usuario.id,
            AvaliacaoRelacionamento.avaliado_id == avaliado_id,
            AvaliacaoRelacionamento.deleted_at.is_(None),
        )
    )
    if relacao is None:
        raise ErroAuth(404, "Relação não encontrada.")
    return relacao


def registrar_resposta_avaliacao(
    db: Session,
    usuario: Usuario,
    relacionamento_id: str,
    pergunta_id: str,
    *,
    valor_numerico: int | None = None,
    valor_texto: str | None = None,
    opcao_id: str | None = None,
) -> AvaliacaoResposta:
    """Grava a nota na relação. Só o avaliador daquela relação."""
    relacao = db.get(AvaliacaoRelacionamento, relacionamento_id)
    if relacao is None or relacao.deleted_at is not None:
        raise ErroAuth(404, "Relação não encontrada.")
    if relacao.avaliador_id != usuario.id:
        raise ErroAuth(404, "Relação não encontrada.")
    ciclo = db.get(CicloAvaliacao, relacao.ciclo_id)
    if ciclo is None or ciclo.deleted_at is not None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    if papel_no_projeto(db, usuario, ciclo.projeto_id) is None:
        raise ErroAuth(404, "Relação não encontrada.")
    pergunta = db.get(Pergunta, pergunta_id)
    if pergunta is None or pergunta.deleted_at is not None:
        raise ErroAuth(422, "Pergunta inválida.")
    pesquisa = db.get(Pesquisa, pergunta.pesquisa_id)
    if (
        pesquisa is None
        or pesquisa.deleted_at is not None
        or pesquisa.tipo != "DESEMPENHO"
        or pesquisa.projeto_id != ciclo.projeto_id
    ):
        raise ErroAuth(422, "Pergunta não pertence a este ciclo.")
    if valor_numerico is None and not (valor_texto or "").strip() and not opcao_id:
        raise ErroAuth(422, "Informe a resposta.")
    if valor_numerico is not None and not isinstance(valor_numerico, int):
        raise ErroAuth(422, "Nota inválida.")
    ja = db.scalar(
        select(AvaliacaoResposta).where(
            AvaliacaoResposta.relacionamento_id == relacao.id,
            AvaliacaoResposta.pergunta_id == pergunta.id,
        )
    )
    if ja is not None:
        raise ErroAuth(409, "Esta pergunta já foi respondida nesta relação.")
    agora_ = agora()
    resposta = AvaliacaoResposta(
        id=novo_id(),
        relacionamento_id=relacao.id,
        pergunta_id=pergunta.id,
        valor_numerico=valor_numerico,
        valor_texto=valor_texto.strip() if valor_texto else None,
        opcao_id=opcao_id,
        respondido_em=agora_,
    )
    relacao.status = "RESPONDIDA"
    relacao.atualizado_em = agora_
    db.add(resposta)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErroAuth(409, "Esta pergunta já foi respondida nesta relação.") from None
    return resposta


def calcular_resultado_avaliacao(
    db: Session,
    usuario: Usuario,
    ciclo_id: str,
    avaliado_id: str,
) -> dict[str, float | None]:
    """Média da relação → média da perspectiva → pesos.

    Consultora e órgão do projeto veem. O avaliado vê a própria nota.
    """
    ciclo = db.get(CicloAvaliacao, ciclo_id)
    if ciclo is None or ciclo.deleted_at is not None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    papel = papel_no_projeto(db, usuario, ciclo.projeto_id)
    if papel in {"CONSULTOR", "ORGAO"}:
        pass
    elif papel == "FUNCIONARIO" and usuario.id == avaliado_id:
        pass
    else:
        raise ErroAuth(404, "Ciclo não encontrado.")

    config = json.loads(ciclo.configuracao) if ciclo.configuracao else {}
    pesos = config.get("pesos", PESOS_PADRAO)
    medias = (
        select(
            AvaliacaoResposta.relacionamento_id.label("rel_id"),
            func.avg(AvaliacaoResposta.valor_numerico).label("media"),
        )
        .where(AvaliacaoResposta.valor_numerico.is_not(None))
        .group_by(AvaliacaoResposta.relacionamento_id)
        .subquery()
    )
    linhas = db.execute(
        select(
            AvaliacaoRelacionamento.tipo_relacao,
            func.avg(medias.c.media),
        )
        .join(medias, medias.c.rel_id == AvaliacaoRelacionamento.id)
        .where(
            AvaliacaoRelacionamento.ciclo_id == ciclo_id,
            AvaliacaoRelacionamento.avaliado_id == avaliado_id,
            AvaliacaoRelacionamento.deleted_at.is_(None),
        )
        .group_by(AvaliacaoRelacionamento.tipo_relacao)
    ).all()
    por_perspectiva = {
        tipo: round(float(media), 2) for tipo, media in linhas if media is not None
    }
    if not por_perspectiva:
        return {"resultado": None, "por_perspectiva": {}}
    soma_pesos = sum(pesos.get(tipo, PESOS_PADRAO[tipo]) for tipo in por_perspectiva)
    if soma_pesos == 0:
        return {"resultado": None, "por_perspectiva": por_perspectiva}
    resultado = sum(
        por_perspectiva[tipo] * pesos.get(tipo, PESOS_PADRAO[tipo])
        for tipo in por_perspectiva
    ) / soma_pesos
    return {
        "resultado": round(resultado, 2),
        "por_perspectiva": por_perspectiva,
    }
