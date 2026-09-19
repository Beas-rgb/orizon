"""CRUD de pesquisas e perguntas; publicação e participantes."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.autorizacao import papel_no_projeto
from app.core.tokens import hash_token, novo_id, novo_token_opaco
from app.models.base import agora
from app.models.configuracao import ConfiguracaoProjeto
from app.models.pesquisa import (
    OpcaoResposta,
    Pergunta,
    Pesquisa,
    PesquisaParticipante,
    TokenResposta,
)
from app.models.projeto import ProjetoUsuario
from app.models.usuario import Usuario
from app.services.auditoria import registrar as _auditar
from app.services.identidade import ErroAuth
from app.services.pesquisa.comum import (
    TIPOS,
    TIPOS_ANONIMOS,
    TIPOS_PERGUNTA,
    _ciente,
    _pesquisa_viva,
    opcoes_da,
)


def criar_pesquisa(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    titulo: str,
    tipo: str,
    descricao: str | None,
) -> Pesquisa:
    if papel_no_projeto(db, consultor, projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    if tipo not in TIPOS:
        raise ErroAuth(422, "Tipo de pesquisa inválido.")
    agora_ = agora()
    pesquisa = Pesquisa(
        id=novo_id(),
        projeto_id=projeto_id,
        criado_por=consultor.id,
        titulo=titulo.strip(),
        descricao=descricao,
        tipo=tipo,
        status="RASCUNHO",
        bloqueada=False,
        criado_em=agora_,
        atualizado_em=agora_,
    )
    db.add(pesquisa)
    _auditar(db, "PESQUISA_CRIADA", consultor.id)
    db.commit()
    return pesquisa


def listar_pesquisas(db: Session, usuario: Usuario, projeto_id: str) -> list[Pesquisa]:
    papel = papel_no_projeto(db, usuario, projeto_id)
    if papel not in {"CONSULTOR", "ORGAO"}:
        raise ErroAuth(404, "Projeto não encontrado.")
    return list(
        db.scalars(
            select(Pesquisa).where(
                Pesquisa.projeto_id == projeto_id,
                Pesquisa.deleted_at.is_(None),
            )
        ).all()
    )


def listar_perguntas_pesquisa(
    db: Session,
    usuario: Usuario,
    pesquisa_id: str,
) -> list[Pergunta]:
    """Consultora do projeto vê a estrutura (rascunho ou publicada). Sem respostas."""
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, usuario, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    return list(
        db.scalars(
            select(Pergunta)
            .where(
                Pergunta.pesquisa_id == pesquisa.id,
                Pergunta.deleted_at.is_(None),
            )
            .order_by(Pergunta.ordem.asc())
        ).all()
    )


def adicionar_pergunta(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    texto: str,
    tipo: str,
    obrigatoria: bool,
    opcoes: list[str],
) -> Pergunta:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if pesquisa.status != "RASCUNHO":
        raise ErroAuth(422, "Pesquisa já publicada. Não altera pergunta.")
    if tipo not in TIPOS_PERGUNTA:
        raise ErroAuth(422, "Tipo de pergunta inválido.")
    if tipo == "SIM_NAO" and not opcoes:
        opcoes = ["Sim", "Não"]
    if tipo in {"MULTIPLA_ESCOLHA", "CHECKBOX", "SIM_NAO"} and len(opcoes) < 2:
        raise ErroAuth(422, "Essa pergunta precisa de opções.")
    ordem = db.scalar(
        select(func.count(Pergunta.id)).where(
            Pergunta.pesquisa_id == pesquisa.id,
            Pergunta.deleted_at.is_(None),
        )
    )
    agora_ = agora()
    pergunta = Pergunta(
        id=novo_id(),
        pesquisa_id=pesquisa.id,
        texto=texto.strip(),
        tipo=tipo,
        obrigatoria=obrigatoria,
        ordem=int(ordem or 0) + 1,
        criado_em=agora_,
        atualizado_em=agora_,
    )
    db.add(pergunta)
    db.flush()
    for indice, texto_opcao in enumerate(opcoes, start=1):
        db.add(
            OpcaoResposta(
                id=novo_id(),
                pergunta_id=pergunta.id,
                texto=texto_opcao.strip(),
                ordem=indice,
                criado_em=agora_,
            )
        )
    pesquisa.atualizado_em = agora_
    _auditar(db, "PERGUNTA_CRIADA", consultor.id)
    db.commit()
    return pergunta


def _exigir_rascunho_consultor(
    db: Session, consultor: Usuario, pesquisa_id: str
) -> Pesquisa:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if pesquisa.status != "RASCUNHO":
        raise ErroAuth(
            422,
            "Pesquisa já publicada. Não altera a estrutura.",
        )
    return pesquisa


def editar_pesquisa(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    titulo: str | None,
    descricao: str | None,
    *,
    descricao_enviada: bool,
) -> Pesquisa:
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    if titulo is None and not descricao_enviada:
        raise ErroAuth(422, "Nada para atualizar.")
    agora_ = agora()
    if titulo is not None:
        pesquisa.titulo = titulo.strip()
    if descricao_enviada:
        pesquisa.descricao = descricao.strip() if descricao else None
    pesquisa.atualizado_em = agora_
    _auditar(db, "PESQUISA_EDITADA", consultor.id)
    db.commit()
    return pesquisa


def editar_pergunta(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
    texto: str | None,
    tipo: str | None,
    obrigatoria: bool | None,
    opcoes: list[str] | None,
) -> Pergunta:
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
    ):
        raise ErroAuth(404, "Pergunta não encontrada.")
    if (
        texto is None
        and tipo is None
        and obrigatoria is None
        and opcoes is None
    ):
        raise ErroAuth(422, "Nada para atualizar.")
    agora_ = agora()
    if texto is not None:
        pergunta.texto = texto.strip()
    if tipo is not None:
        if tipo not in TIPOS_PERGUNTA:
            raise ErroAuth(422, "Tipo de pergunta inválido.")
        pergunta.tipo = tipo
    if obrigatoria is not None:
        pergunta.obrigatoria = obrigatoria
    tipo_final = pergunta.tipo
    if opcoes is not None:
        textos = [item.strip() for item in opcoes if item.strip()]
        if tipo_final == "SIM_NAO" and not textos:
            textos = ["Sim", "Não"]
        if tipo_final in {"MULTIPLA_ESCOLHA", "CHECKBOX", "SIM_NAO"} and len(
            textos
        ) < 2:
            raise ErroAuth(422, "Essa pergunta precisa de opções.")
        antigas = db.scalars(
            select(OpcaoResposta).where(OpcaoResposta.pergunta_id == pergunta.id)
        ).all()
        for antiga in antigas:
            db.delete(antiga)
        db.flush()
        for indice, texto_opcao in enumerate(textos, start=1):
            db.add(
                OpcaoResposta(
                    id=novo_id(),
                    pergunta_id=pergunta.id,
                    texto=texto_opcao,
                    ordem=indice,
                    criado_em=agora_,
                )
            )
    elif tipo is not None and tipo_final in {
        "MULTIPLA_ESCOLHA",
        "CHECKBOX",
        "SIM_NAO",
    }:
        existentes = opcoes_da(db, pergunta.id)
        if len(existentes) < 2 and tipo_final != "SIM_NAO":
            raise ErroAuth(422, "Essa pergunta precisa de opções.")
        if tipo_final == "SIM_NAO" and len(existentes) < 2:
            for indice, texto_opcao in enumerate(["Sim", "Não"], start=1):
                db.add(
                    OpcaoResposta(
                        id=novo_id(),
                        pergunta_id=pergunta.id,
                        texto=texto_opcao,
                        ordem=indice,
                        criado_em=agora_,
                    )
                )
    pergunta.atualizado_em = agora_
    pesquisa.atualizado_em = agora_
    _auditar(db, "PERGUNTA_EDITADA", consultor.id)
    db.commit()
    return pergunta


def excluir_pergunta(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
) -> None:
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
    ):
        raise ErroAuth(404, "Pergunta não encontrada.")
    agora_ = agora()
    pergunta.deleted_at = agora_
    pergunta.atualizado_em = agora_
    vivas = list(
        db.scalars(
            select(Pergunta)
            .where(
                Pergunta.pesquisa_id == pesquisa.id,
                Pergunta.deleted_at.is_(None),
            )
            .order_by(Pergunta.ordem)
        ).all()
    )
    for indice, viva in enumerate(vivas, start=1):
        viva.ordem = indice
        viva.atualizado_em = agora_
    pesquisa.atualizado_em = agora_
    _auditar(db, "PERGUNTA_EXCLUIDA", consultor.id)
    db.commit()


def reordenar_perguntas(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    pergunta_ids: list[str],
) -> list[Pergunta]:
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    vivas = list(
        db.scalars(
            select(Pergunta).where(
                Pergunta.pesquisa_id == pesquisa.id,
                Pergunta.deleted_at.is_(None),
            )
        ).all()
    )
    por_id = {item.id: item for item in vivas}
    if len(pergunta_ids) != len(vivas) or set(pergunta_ids) != set(por_id):
        raise ErroAuth(
            422,
            "A lista de reordenação deve incluir todas as perguntas ativas.",
        )
    agora_ = agora()
    for indice, pergunta_id in enumerate(pergunta_ids, start=1):
        pergunta = por_id[pergunta_id]
        pergunta.ordem = indice
        pergunta.atualizado_em = agora_
    pesquisa.atualizado_em = agora_
    _auditar(db, "PERGUNTAS_REORDENADAS", consultor.id)
    db.commit()
    return list(
        db.scalars(
            select(Pergunta)
            .where(
                Pergunta.pesquisa_id == pesquisa.id,
                Pergunta.deleted_at.is_(None),
            )
            .order_by(Pergunta.ordem)
        ).all()
    )


def _criar_token_resposta(
    db: Session,
    pesquisa: Pesquisa,
    *,
    usado: bool = False,
    usado_em=None,
) -> tuple[str, str]:
    """Grava só o hash. Devolve (id, plaintext) — plaintext só na criação."""
    plain = novo_token_opaco()
    tid = novo_id()
    db.add(
        TokenResposta(
            id=tid,
            pesquisa_id=pesquisa.id,
            setor_id=None,
            token_hash=hash_token(plain),
            usado=usado,
            usado_em=usado_em,
            expira_em=pesquisa.disponivel_ate,
            criado_em=agora(),
        )
    )
    return tid, plain


def publicar(db: Session, consultor: Usuario, pesquisa_id: str, *, tarefas=None) -> Pesquisa:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if pesquisa.status != "RASCUNHO":
        raise ErroAuth(422, "Só rascunho pode ser publicado.")
    config = db.scalar(
        select(ConfiguracaoProjeto).where(
            ConfiguracaoProjeto.projeto_id == pesquisa.projeto_id
        )
    )
    if config is None or not config.pesquisas_habilitadas:
        raise ErroAuth(422, "Ligue as pesquisas na configuração do projeto.")
    tem = db.scalar(
        select(Pergunta.id).where(
            Pergunta.pesquisa_id == pesquisa.id,
            Pergunta.deleted_at.is_(None),
        )
    )
    if tem is None:
        raise ErroAuth(422, "Inclua ao menos uma pergunta.")
    agora_ = agora()
    pesquisa.status = "PUBLICADA"
    pesquisa.publicada_em = agora_
    pesquisa.disponivel_de = agora_
    pesquisa.disponivel_ate = agora_ + timedelta(days=14)
    pesquisa.atualizado_em = agora_
    _auditar(db, "PESQUISA_PUBLICADA", consultor.id)
    _sincronizar_participantes(db, pesquisa)
    from app.services.notificacao import avisar, membros_orgao

    for membro in membros_orgao(db, pesquisa.projeto_id):
        avisar(
            db,
            membro,
            "PESQUISA",
            "Pesquisa publicada",
            f"A pesquisa {pesquisa.titulo} está aberta.",
            pesquisa.projeto_id,
            "EMAIL",
            "PESQUISA_PUBLICADA",
            tarefas=tarefas,
        )
    db.commit()
    return pesquisa


def _sincronizar_participantes(db: Session, pesquisa: Pesquisa) -> None:
    """Cria PENDENTE para cada FUNCIONÁRIO do projeto e garante 1 token de entrada."""
    agora_ = agora()
    vinculos = db.scalars(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == pesquisa.projeto_id,
            ProjetoUsuario.papel == "FUNCIONARIO",
        )
    ).all()
    for vinculo in vinculos:
        existe = db.scalar(
            select(PesquisaParticipante.id).where(
                PesquisaParticipante.pesquisa_id == pesquisa.id,
                PesquisaParticipante.usuario_id == vinculo.usuario_id,
                PesquisaParticipante.deleted_at.is_(None),
            )
        )
        if existe is not None:
            continue
        db.add(
            PesquisaParticipante(
                id=novo_id(),
                pesquisa_id=pesquisa.id,
                usuario_id=vinculo.usuario_id,
                status="PENDENTE",
                token_id=None,
                iniciado_em=None,
                respondido_em=None,
                criado_em=agora_,
                atualizado_em=agora_,
                deleted_at=None,
            )
        )
    existe_entrada = db.scalar(
        select(TokenResposta.id)
        .where(TokenResposta.pesquisa_id == pesquisa.id)
        .order_by(TokenResposta.criado_em.asc())
        .limit(1)
    )
    if existe_entrada is None:
        _criar_token_resposta(db, pesquisa)


def listar_minhas_pesquisas(db: Session, usuario: Usuario) -> list[dict]:
    """Pesquisas PUBLICADAS dos projetos do funcionário + status.

    GET puro: não cria participante nem token. Resposta usa
    `/eu/pesquisas/{id}/formulario` (autenticado).
    """
    if usuario.papel != "FUNCIONARIO":
        return []
    projeto_ids = list(
        db.scalars(
            select(ProjetoUsuario.projeto_id).where(
                ProjetoUsuario.usuario_id == usuario.id,
                ProjetoUsuario.papel == "FUNCIONARIO",
            )
        ).all()
    )
    if not projeto_ids:
        return []
    pesquisas = db.scalars(
        select(Pesquisa)
        .where(
            Pesquisa.projeto_id.in_(projeto_ids),
            Pesquisa.status == "PUBLICADA",
            Pesquisa.deleted_at.is_(None),
            Pesquisa.bloqueada.is_(False),
        )
        .order_by(Pesquisa.publicada_em.desc())
    ).all()
    saida: list[dict] = []
    for pesquisa in pesquisas:
        participante = db.scalar(
            select(PesquisaParticipante).where(
                PesquisaParticipante.pesquisa_id == pesquisa.id,
                PesquisaParticipante.usuario_id == usuario.id,
                PesquisaParticipante.deleted_at.is_(None),
            )
        )
        status = participante.status if participante else "PENDENTE"
        prazo = _ciente(pesquisa.disponivel_ate)
        saida.append(
            {
                "pesquisa_id": pesquisa.id,
                "projeto_id": pesquisa.projeto_id,
                "titulo": pesquisa.titulo,
                "tipo": pesquisa.tipo,
                "status_participacao": status,
                "disponivel_ate": prazo.isoformat() if prazo else None,
                "token": None,
            }
        )
    return saida


def listar_participantes_status(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
) -> dict:
    """CLIMA: só totais. Demais tipos: funcionários + status (sem respostas)."""
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    vinculos = db.scalars(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == pesquisa.projeto_id,
            ProjetoUsuario.papel == "FUNCIONARIO",
        )
    ).all()
    total = 0
    respondidas = 0
    itens: list[dict] = []
    for vinculo in vinculos:
        pessoa = db.get(Usuario, vinculo.usuario_id)
        if pessoa is None or pessoa.deleted_at is not None:
            continue
        total += 1
        participante = db.scalar(
            select(PesquisaParticipante).where(
                PesquisaParticipante.pesquisa_id == pesquisa.id,
                PesquisaParticipante.usuario_id == pessoa.id,
                PesquisaParticipante.deleted_at.is_(None),
            )
        )
        status = participante.status if participante else "PENDENTE"
        if status == "RESPONDIDA":
            respondidas += 1
        itens.append(
            {
                "usuario_id": pessoa.id,
                "nome": pessoa.nome,
                "email": pessoa.email,
                "status": status,
            }
        )
    if pesquisa.tipo in TIPOS_ANONIMOS:
        return {
            "agregado": True,
            "total": total,
            "respondidas": respondidas,
            "itens": None,
        }
    itens.sort(key=lambda item: (item["status"], item["nome"].lower()))
    return {
        "agregado": False,
        "total": total,
        "respondidas": respondidas,
        "itens": itens,
    }


def encerrar(db: Session, consultor: Usuario, pesquisa_id: str) -> Pesquisa:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if pesquisa.status != "PUBLICADA":
        raise ErroAuth(422, "Só pesquisa publicada pode ser encerrada.")
    agora_ = agora()
    pesquisa.status = "ENCERRADA"
    pesquisa.bloqueada = True
    pesquisa.encerrada_em = agora_
    pesquisa.atualizado_em = agora_
    _auditar(db, "PESQUISA_ENCERRADA", consultor.id)
    db.commit()
    return pesquisa
