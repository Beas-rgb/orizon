"""Motor da avaliação de desempenho: ciclo, relações e cálculo.

Não toca em CLIMA. TIPOS_ANONIMOS continua {"CLIMA"}.
"""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.autorizacao import exigir_papel, papel_no_projeto
from app.core.tokens import novo_id
from app.models.base import agora
from app.models.desempenho import AvaliacaoRelacionamento, CicloAvaliacao
from app.models.estrutura import PerfilFuncionario
from app.models.pesquisa import Resposta
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


def calcular_resultado_avaliacao(
    db: Session,
    ciclo_id: str,
    avaliado_id: str,
) -> dict[str, float | None]:
    """Média por pergunta → consolidação por perspectiva → pesos → resultado.

    Exemplo: AUTO 4,0×1 + SUPERIOR 4,5×2 + SUBORDINADOS 4,2×1 → 4,30.
    """
    ciclo = db.get(CicloAvaliacao, ciclo_id)
    if ciclo is None or ciclo.deleted_at is not None:
        raise ErroAuth(404, "Ciclo não encontrado.")
    relacoes = db.scalars(
        select(AvaliacaoRelacionamento).where(
            AvaliacaoRelacionamento.ciclo_id == ciclo_id,
            AvaliacaoRelacionamento.avaliado_id == avaliado_id,
            AvaliacaoRelacionamento.deleted_at.is_(None),
        )
    ).all()
    if not relacoes:
        return {"resultado": None, "por_perspectiva": {}}

    config = json.loads(ciclo.configuracao) if ciclo.configuracao else {}
    pesos = config.get("pesos", PESOS_PADRAO)
    agregacao = config.get("agregacao", "MEDIA")

    por_perspectiva: dict[str, float] = {}
    for tipo in TIPOS_RELACAO:
        relacoes_tipo = [r for r in relacoes if r.tipo_relacao == tipo]
        if not relacoes_tipo:
            continue
        notas = []
        for relacao in relacoes_tipo:
            media = db.scalar(
                select(func.avg(Resposta.valor_numerico)).where(
                    Resposta.token_id == relacao.id,
                    Resposta.valor_numerico.is_not(None),
                )
            )
            if media is not None:
                notas.append(float(media))
        if notas:
            if agregacao == "MEDIA":
                por_perspectiva[tipo] = round(sum(notas) / len(notas), 2)
            else:
                por_perspectiva[tipo] = round(sum(notas) / len(notas), 2)

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
