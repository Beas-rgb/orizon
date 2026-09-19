"""Pesquisa. Clima não diz quem respondeu. Desempenho devolve a nota
só a quem tem o token. O órgão vê agregado, nunca a lista de pessoas.
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.autorizacao import papel_no_projeto
from app.core.tokens import hash_token, novo_id, novo_token_opaco
from app.integrations.arquivos import (
    ArquivoInvalido,
    copiar_midia,
    guardar_midia,
    ler_midia,
)
from app.models.auditoria import LogAuditoria
from app.models.base import agora
from app.models.configuracao import ConfiguracaoProjeto
from app.models.controle_acesso import ControleAcesso
from app.models.pesquisa import (
    OpcaoResposta,
    Pergunta,
    Pesquisa,
    PesquisaParticipante,
    Resposta,
    TemplateOpcao,
    TemplatePergunta,
    TemplatePesquisa,
    TokenResposta,
)
from app.models.projeto import Projeto, ProjetoUsuario
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth

TIPOS = {"CLIMA", "DESEMPENHO", "CARGOS_SALARIOS", "PERSONALIZADA"}
TIPOS_PERGUNTA = {
    "TEXTO_LIVRE",
    "NOTA_5",
    "NOTA_10",
    "SIM_NAO",
    "MULTIPLA_ESCOLHA",
    "CHECKBOX",
}
RESPONDER_MAX_TENTATIVAS = 10
RESPONDER_JANELA_MINUTOS = 5
# Painel omite média/distribuição quando há menos respondentes distintos.
K_ANONIMATO = 5
TIPOS_ANONIMOS = {"CLIMA"}


def _ciente(valor):
    if valor is None:
        return None
    if valor.tzinfo is None:
        from datetime import UTC

        return valor.replace(tzinfo=UTC)
    return valor


def _auditar(db: Session, acao: str, usuario_id: str | None) -> None:
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=usuario_id,
            acao=acao,
            criado_em=agora(),
        )
    )


def _pesquisa_viva(db: Session, pesquisa_id: str) -> Pesquisa:
    pesquisa = db.get(Pesquisa, pesquisa_id)
    if pesquisa is None or pesquisa.deleted_at is not None:
        raise ErroAuth(404, "Pesquisa não encontrada.")
    return pesquisa


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


def anexar_midia_pergunta(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
    conteudo: bytes,
) -> Pergunta:
    """Upload de foto/vídeo. Só em RASCUNHO. Chave interna, nunca o nome do arquivo."""
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
    ):
        raise ErroAuth(404, "Pergunta não encontrada.")
    objeto_id = novo_id()
    try:
        chave, midia_tipo, _mime = guardar_midia(objeto_id, conteudo)
    except ArquivoInvalido as exc:
        raise ErroAuth(422, str(exc)) from None
    pergunta.midia_key = chave
    pergunta.midia_tipo = midia_tipo
    pergunta.atualizado_em = agora()
    pesquisa.atualizado_em = pergunta.atualizado_em
    _auditar(db, "PERGUNTA_MIDIA", consultor.id)
    db.commit()
    return pergunta


def remover_midia_pergunta(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
) -> Pergunta:
    pesquisa = _exigir_rascunho_consultor(db, consultor, pesquisa_id)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
    ):
        raise ErroAuth(404, "Pergunta não encontrada.")
    pergunta.midia_key = None
    pergunta.midia_tipo = None
    pergunta.atualizado_em = agora()
    pesquisa.atualizado_em = pergunta.atualizado_em
    _auditar(db, "PERGUNTA_MIDIA_REMOVIDA", consultor.id)
    db.commit()
    return pergunta


def baixar_midia_pergunta(
    db: Session,
    usuario: Usuario,
    pesquisa_id: str,
    pergunta_id: str,
) -> tuple[bytes, str]:
    """Consultora (qualquer status). Órgão/funcionário só PUBLICADA/ENCERRADA."""
    from app.core.autorizacao import exigir_midia_pesquisa, exigir_pesquisa_viva

    pesquisa = exigir_pesquisa_viva(db, pesquisa_id)
    exigir_midia_pesquisa(db, usuario, pesquisa)
    pergunta = db.get(Pergunta, pergunta_id)
    if (
        pergunta is None
        or pergunta.pesquisa_id != pesquisa.id
        or pergunta.deleted_at is not None
        or not pergunta.midia_key
    ):
        raise ErroAuth(404, "Mídia não encontrada.")
    try:
        conteudo = ler_midia(pergunta.midia_key)
    except FileNotFoundError:
        raise ErroAuth(404, "Mídia não encontrada.") from None
    mime = "application/octet-stream"
    if pergunta.midia_tipo == "IMAGEM":
        mime = "image/jpeg"
    elif pergunta.midia_tipo == "VIDEO":
        mime = "video/mp4"
    from app.integrations.arquivos import detectar_mime

    detectado = detectar_mime(conteudo)
    if detectado:
        mime = detectado
    return conteudo, mime


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
    """Pesquisas PUBLICADAS dos projetos do funcionário + status de participação."""
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
    agora_ = agora()
    for pesquisa in pesquisas:
        participante = db.scalar(
            select(PesquisaParticipante).where(
                PesquisaParticipante.pesquisa_id == pesquisa.id,
                PesquisaParticipante.usuario_id == usuario.id,
                PesquisaParticipante.deleted_at.is_(None),
            )
        )
        if participante is None:
            participante = PesquisaParticipante(
                id=novo_id(),
                pesquisa_id=pesquisa.id,
                usuario_id=usuario.id,
                status="PENDENTE",
                token_id=None,
                iniciado_em=None,
                respondido_em=None,
                criado_em=agora_,
                atualizado_em=agora_,
                deleted_at=None,
            )
            db.add(participante)
            db.flush()
        # Hash no banco: emite plaintext fresco só para o painel do funcionário.
        token = None
        if participante.status != "RESPONDIDA":
            _sincronizar_participantes(db, pesquisa)
            _, token = _criar_token_resposta(db, pesquisa)
        prazo = _ciente(pesquisa.disponivel_ate)
        saida.append(
            {
                "pesquisa_id": pesquisa.id,
                "projeto_id": pesquisa.projeto_id,
                "titulo": pesquisa.titulo,
                "tipo": pesquisa.tipo,
                "status_participacao": participante.status,
                "disponivel_ate": prazo.isoformat() if prazo else None,
                "token": token,
            }
        )
    db.commit()
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


def baixar_midia_pelo_token(
    db: Session,
    token: str,
    pergunta_id: str,
    usuario: Usuario,
) -> tuple[bytes, str]:
    """Mesma autorização do formulário de resposta."""
    linha = _token_convite(db, token)
    pesquisa = _pesquisa_viva(db, linha.pesquisa_id)
    _participante_da_pesquisa(db, usuario, pesquisa, para_envio=False)
    db.commit()
    return baixar_midia_pergunta(db, usuario, pesquisa.id, pergunta_id)


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


def salvar_modelo(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    nome: str,
) -> TemplatePesquisa:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    agora_ = agora()
    modelo = TemplatePesquisa(
        id=novo_id(),
        criado_por=consultor.id,
        nome=nome.strip(),
        descricao=pesquisa.descricao,
        tipo=pesquisa.tipo,
        categoria="generico",
        compartilhado=False,
        versao=1,
        ativo=True,
        organizacao_id=None,
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )
    db.add(modelo)
    db.flush()
    perguntas = db.scalars(
        select(Pergunta)
        .where(
            Pergunta.pesquisa_id == pesquisa.id,
            Pergunta.deleted_at.is_(None),
        )
        .order_by(Pergunta.ordem)
    ).all()
    for item in perguntas:
        midia_key = None
        midia_tipo = item.midia_tipo
        if item.midia_key:
            try:
                midia_key = copiar_midia(item.midia_key, novo_id())
            except (ArquivoInvalido, FileNotFoundError, OSError):
                midia_key = None
                midia_tipo = None
        copia = TemplatePergunta(
            id=novo_id(),
            template_id=modelo.id,
            texto=item.texto,
            tipo=item.tipo,
            obrigatoria=item.obrigatoria,
            ordem=item.ordem,
            midia_tipo=midia_tipo if midia_key else None,
            midia_key=midia_key,
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
        db.add(copia)
        db.flush()
        opcoes = db.scalars(
            select(OpcaoResposta)
            .where(OpcaoResposta.pergunta_id == item.id)
            .order_by(OpcaoResposta.ordem)
        ).all()
        for opcao in opcoes:
            db.add(
                TemplateOpcao(
                    id=novo_id(),
                    pergunta_template_id=copia.id,
                    texto=opcao.texto,
                    ordem=opcao.ordem,
                    criado_em=agora_,
                    atualizado_em=agora_,
                    deleted_at=None,
                )
            )
    _auditar(db, "MODELO_SALVO", consultor.id)
    db.commit()
    return modelo


def listar_modelos(db: Session, consultor: Usuario) -> list[TemplatePesquisa]:
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(404, "Modelo não encontrado.")
    return list(
        db.scalars(
            select(TemplatePesquisa)
            .where(
                TemplatePesquisa.deleted_at.is_(None),
                TemplatePesquisa.ativo.is_(True),
                TemplatePesquisa.criado_por == consultor.id,
            )
            .order_by(TemplatePesquisa.criado_em.desc())
        ).all()
    )


def criar_de_modelo(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    template_id: str,
    titulo: str | None,
) -> Pesquisa:
    if papel_no_projeto(db, consultor, projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    modelo = db.get(TemplatePesquisa, template_id)
    if (
        modelo is None
        or modelo.deleted_at is not None
        or not modelo.ativo
        or modelo.criado_por != consultor.id
    ):
        raise ErroAuth(404, "Modelo não encontrado.")
    agora_ = agora()
    pesquisa = Pesquisa(
        id=novo_id(),
        projeto_id=projeto_id,
        criado_por=consultor.id,
        titulo=(titulo or modelo.nome).strip(),
        descricao=modelo.descricao,
        tipo=modelo.tipo,
        status="RASCUNHO",
        bloqueada=False,
        criado_em=agora_,
        atualizado_em=agora_,
        template_origem_id=modelo.id,
    )
    db.add(pesquisa)
    db.flush()
    perguntas = db.scalars(
        select(TemplatePergunta)
        .where(
            TemplatePergunta.template_id == modelo.id,
            TemplatePergunta.deleted_at.is_(None),
        )
        .order_by(TemplatePergunta.ordem)
    ).all()
    for item in perguntas:
        midia_key = None
        midia_tipo = item.midia_tipo
        if item.midia_key:
            try:
                midia_key = copiar_midia(item.midia_key, novo_id())
            except (ArquivoInvalido, FileNotFoundError, OSError):
                midia_key = None
                midia_tipo = None
        pergunta = Pergunta(
            id=novo_id(),
            pesquisa_id=pesquisa.id,
            texto=item.texto,
            tipo=item.tipo,
            obrigatoria=item.obrigatoria,
            ordem=item.ordem,
            midia_tipo=midia_tipo if midia_key else None,
            midia_key=midia_key,
            criado_em=agora_,
            atualizado_em=agora_,
        )
        db.add(pergunta)
        db.flush()
        opcoes = db.scalars(
            select(TemplateOpcao)
            .where(
                TemplateOpcao.pergunta_template_id == item.id,
                TemplateOpcao.deleted_at.is_(None),
            )
            .order_by(TemplateOpcao.ordem)
        ).all()
        for opcao in opcoes:
            db.add(
                OpcaoResposta(
                    id=novo_id(),
                    pergunta_id=pergunta.id,
                    texto=opcao.texto,
                    ordem=opcao.ordem,
                    criado_em=agora_,
                )
            )
    _auditar(db, "PESQUISA_DE_MODELO", consultor.id)
    db.commit()
    return pesquisa


def gerar_tokens(
    db: Session,
    consultor: Usuario,
    pesquisa_id: str,
    quantidade: int,
) -> list[str]:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if papel_no_projeto(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if pesquisa.status != "PUBLICADA":
        raise ErroAuth(422, "Publique a pesquisa antes de gerar o link.")
    if quantidade < 1 or quantidade > 500:
        raise ErroAuth(
            422,
            "Gere até 500 links por vez. Pode repetir até cobrir todos.",
        )
    links: list[str] = []
    for _ in range(quantidade):
        _, plain = _criar_token_resposta(db, pesquisa)
        links.append(plain)
    _auditar(db, "TOKENS_GERADOS", consultor.id)
    db.commit()
    return links


def _token_convite(db: Session, token: str) -> TokenResposta:
    """Resolve o link de entrada. Não exige `usado` — o controle é o participante."""
    linha = db.scalar(
        select(TokenResposta).where(TokenResposta.token_hash == hash_token(token))
    )
    if linha is None:
        raise ErroAuth(404, "Link inválido ou já usado.")
    pesquisa = _pesquisa_viva(db, linha.pesquisa_id)
    if pesquisa.status != "PUBLICADA" or pesquisa.bloqueada:
        raise ErroAuth(404, "Link inválido ou já usado.")
    agora_ = agora()
    limite = _ciente(pesquisa.disponivel_ate)
    if limite and limite < agora_:
        raise ErroAuth(404, "Link inválido ou já usado.")
    return linha


def _autorizar_funcionario_na_pesquisa(
    db: Session,
    usuario: Usuario,
    pesquisa: Pesquisa,
) -> None:
    """Só FUNCIONÁRIO com vínculo ativo no projeto. Demais papéis → 404."""
    if usuario.papel != "FUNCIONARIO":
        raise ErroAuth(404, "Link inválido ou já usado.")
    if papel_no_projeto(db, usuario, pesquisa.projeto_id) != "FUNCIONARIO":
        raise ErroAuth(404, "Link inválido ou já usado.")


def _participante_da_pesquisa(
    db: Session,
    usuario: Usuario,
    pesquisa: Pesquisa,
    *,
    para_envio: bool,
) -> PesquisaParticipante:
    """Garante participante + token pessoal. Segunda resposta → 409."""
    _autorizar_funcionario_na_pesquisa(db, usuario, pesquisa)
    agora_ = agora()
    participante = db.scalar(
        select(PesquisaParticipante).where(
            PesquisaParticipante.pesquisa_id == pesquisa.id,
            PesquisaParticipante.usuario_id == usuario.id,
            PesquisaParticipante.deleted_at.is_(None),
        )
    )
    if participante is None:
        participante = PesquisaParticipante(
            id=novo_id(),
            pesquisa_id=pesquisa.id,
            usuario_id=usuario.id,
            status="PENDENTE",
            token_id=None,
            iniciado_em=None,
            respondido_em=None,
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
        db.add(participante)
        db.flush()
    if participante.status == "RESPONDIDA":
        raise ErroAuth(409, "Você já respondeu esta pesquisa.")
    if participante.status in {"EXPIRADA", "CANCELADA"}:
        raise ErroAuth(404, "Link inválido ou já usado.")
    if participante.token_id is None:
        tid, _plain = _criar_token_resposta(db, pesquisa)
        db.flush()
        participante.token_id = tid
    if participante.status == "PENDENTE":
        participante.status = "EM_ANDAMENTO"
        participante.iniciado_em = agora_
        participante.atualizado_em = agora_
    elif para_envio and participante.status == "EM_ANDAMENTO":
        participante.atualizado_em = agora_
    db.flush()
    return participante


def _token_pessoal(db: Session, participante: PesquisaParticipante) -> TokenResposta:
    if not participante.token_id:
        raise ErroAuth(404, "Link inválido ou já usado.")
    linha = db.get(TokenResposta, participante.token_id)
    if linha is None or linha.usado:
        raise ErroAuth(404, "Link inválido ou já usado.")
    return linha


def perguntas_do_token(
    db: Session,
    token: str,
    usuario: Usuario,
) -> tuple[Pesquisa, list[Pergunta]]:
    convite = _token_convite(db, token)
    pesquisa = _pesquisa_viva(db, convite.pesquisa_id)
    _participante_da_pesquisa(db, usuario, pesquisa, para_envio=False)
    db.commit()
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
    return pesquisa, perguntas


def opcoes_da(db: Session, pergunta_id: str) -> list[OpcaoResposta]:
    return list(
        db.scalars(
            select(OpcaoResposta)
            .where(OpcaoResposta.pergunta_id == pergunta_id)
            .order_by(OpcaoResposta.ordem)
        ).all()
    )


def registrar_respostas(
    db: Session,
    token: str,
    itens: list[dict],
    usuario: Usuario,
    ip: str | None = None,
) -> tuple[str, float | None]:
    _rate_limit_responder(db, usuario.id, ip)
    # Persiste a contagem mesmo se o envio falhar depois (422) e der rollback.
    db.commit()
    convite = _token_convite(db, token)
    pesquisa = _pesquisa_viva(db, convite.pesquisa_id)
    participante = _participante_da_pesquisa(
        db, usuario, pesquisa, para_envio=True
    )
    linha = _token_pessoal(db, participante)
    perguntas = {
        item.id: item
        for item in db.scalars(
            select(Pergunta).where(
                Pergunta.pesquisa_id == pesquisa.id,
                Pergunta.deleted_at.is_(None),
            )
        ).all()
    }
    if not itens:
        raise ErroAuth(422, "Envie as respostas.")
    _validar_obrigatorias(perguntas, itens)
    agora_ = agora()
    # CLIMA: respostas em token anônimo (sem FK para participante/usuário).
    if pesquisa.tipo in TIPOS_ANONIMOS:
        token_resposta_id, _plain = _criar_token_resposta(
            db, pesquisa, usado=True, usado_em=agora_
        )
        db.flush()
        participante.token_id = None
    else:
        token_resposta_id = linha.id
        linha.usado = True
        linha.usado_em = agora_

    for item in itens:
        pergunta = perguntas.get(item["pergunta_id"])
        if pergunta is None:
            raise ErroAuth(422, "Pergunta inválida.")
        numerico, texto, opcoes = _normalizar(db, pergunta, item)
        if isinstance(opcoes, list):
            for opcao_id in opcoes:
                db.add(
                    Resposta(
                        id=novo_id(),
                        token_id=token_resposta_id,
                        pergunta_id=pergunta.id,
                        valor_texto=None,
                        valor_numerico=None,
                        opcao_id=opcao_id,
                        respondido_em=agora_,
                    )
                )
        else:
            db.add(
                Resposta(
                    id=novo_id(),
                    token_id=token_resposta_id,
                    pergunta_id=pergunta.id,
                    valor_texto=texto,
                    valor_numerico=numerico,
                    opcao_id=opcoes,
                    respondido_em=agora_,
                )
            )
    participante.status = "RESPONDIDA"
    participante.respondido_em = agora_
    participante.atualizado_em = agora_
    _limpar_rate_responder(db, usuario.id, ip)
    projeto = db.get(Projeto, pesquisa.projeto_id)
    if projeto is not None:
        consultor = db.get(Usuario, projeto.consultor_id)
        if consultor is not None:
            from app.services.notificacao import avisar

            avisar(
                db,
                consultor,
                "PESQUISA",
                "Nova resposta",
                f"Uma resposta chegou na pesquisa {pesquisa.titulo}.",
                pesquisa.projeto_id,
                "EMAIL",
                "RESPOSTA",
            )
    # CLIMA: auditoria sem usuario_id (não amarra quem respondeu).
    if pesquisa.tipo in TIPOS_ANONIMOS:
        _auditar(db, "PESQUISA_RESPONDIDA", None)
    else:
        _auditar(db, "PESQUISA_RESPONDIDA", usuario.id)
    db.commit()
    if pesquisa.tipo == "DESEMPENHO":
        return pesquisa.tipo, _nota_do_token(db, linha.id)
    return pesquisa.tipo, None


def _chaves_rate_responder(usuario_id: str, ip: str | None) -> list[str]:
    chaves = [f"responder:user:{usuario_id}"]
    if ip:
        chaves.append(f"responder:ip:{ip}")
    return chaves


def _rate_limit_responder(
    db: Session, usuario_id: str, ip: str | None
) -> None:
    """10 tentativas / 5 min por usuário e por IP (ControleAcesso)."""
    agora_ = agora()
    janela = timedelta(minutes=RESPONDER_JANELA_MINUTOS)
    for chave in _chaves_rate_responder(usuario_id, ip):
        linha = db.get(ControleAcesso, chave)
        if linha is None:
            linha = ControleAcesso(
                chave=chave,
                tentativas=0,
                bloqueado_ate=None,
                atualizado_em=agora_,
            )
            db.add(linha)
            db.flush()
        bloqueado = _ciente(linha.bloqueado_ate)
        if bloqueado and bloqueado > agora_:
            raise ErroAuth(
                429,
                "Muitas tentativas. Aguarde alguns minutos e tente de novo.",
            )
        atualizado = _ciente(linha.atualizado_em) or agora_
        if agora_ - atualizado > janela:
            linha.tentativas = 0
            linha.bloqueado_ate = None
        linha.tentativas += 1
        linha.atualizado_em = agora_
        if linha.tentativas > RESPONDER_MAX_TENTATIVAS:
            linha.bloqueado_ate = agora_ + janela
            db.flush()
            raise ErroAuth(
                429,
                "Muitas tentativas. Aguarde alguns minutos e tente de novo.",
            )
    db.flush()


def _limpar_rate_responder(
    db: Session, usuario_id: str, ip: str | None
) -> None:
    agora_ = agora()
    for chave in _chaves_rate_responder(usuario_id, ip):
        linha = db.get(ControleAcesso, chave)
        if linha is None:
            continue
        linha.tentativas = 0
        linha.bloqueado_ate = None
        linha.atualizado_em = agora_


def _validar_obrigatorias(
    perguntas: dict[str, Pergunta], itens: list[dict]
) -> None:
    enviadas = {item["pergunta_id"] for item in itens}
    faltando = [
        pergunta.texto
        for pergunta in perguntas.values()
        if pergunta.obrigatoria and pergunta.id not in enviadas
    ]
    if faltando:
        raise ErroAuth(
            422,
            "Faltam respostas obrigatórias: " + "; ".join(faltando),
        )


def nota_do_token(
    db: Session,
    token: str,
    usuario: Usuario,
) -> tuple[str, float | None]:
    convite = _token_convite(db, token)
    pesquisa = _pesquisa_viva(db, convite.pesquisa_id)
    _autorizar_funcionario_na_pesquisa(db, usuario, pesquisa)
    participante = db.scalar(
        select(PesquisaParticipante).where(
            PesquisaParticipante.pesquisa_id == pesquisa.id,
            PesquisaParticipante.usuario_id == usuario.id,
            PesquisaParticipante.deleted_at.is_(None),
        )
    )
    if participante is None or participante.status != "RESPONDIDA":
        raise ErroAuth(404, "Link inválido ou já usado.")
    if pesquisa.tipo != "DESEMPENHO":
        return pesquisa.tipo, None
    if not participante.token_id:
        return pesquisa.tipo, None
    return pesquisa.tipo, _nota_do_token(db, participante.token_id)


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


def _nota_do_token(db: Session, token_id: str) -> float | None:
    media = db.scalar(
        select(func.avg(Resposta.valor_numerico)).where(
            Resposta.token_id == token_id,
            Resposta.valor_numerico.is_not(None),
        )
    )
    return round(float(media), 2) if media is not None else None


def _normalizar(
    db: Session, pergunta: Pergunta, item: dict
) -> tuple[int | None, str | None, str | list[str] | None]:
    if pergunta.tipo == "TEXTO_LIVRE":
        texto = (item.get("valor_texto") or "").strip()
        if pergunta.obrigatoria and not texto:
            raise ErroAuth(422, "Resposta obrigatória.")
        return None, texto, None
    if pergunta.tipo in {"NOTA_5", "NOTA_10"}:
        nota = item.get("valor_numerico")
        teto = 5 if pergunta.tipo == "NOTA_5" else 10
        if nota is None or nota < 1 or nota > teto:
            raise ErroAuth(422, "Nota fora da escala.")
        return nota, None, None
    if pergunta.tipo == "CHECKBOX":
        brutos = list(item.get("opcao_ids") or [])
        unico = item.get("opcao_id")
        if unico:
            brutos.append(unico)
        vistos: list[str] = []
        for opcao_id in brutos:
            if opcao_id and opcao_id not in vistos:
                vistos.append(opcao_id)
        if pergunta.obrigatoria and not vistos:
            raise ErroAuth(422, "Resposta obrigatória.")
        for opcao_id in vistos:
            opcao = db.get(OpcaoResposta, opcao_id)
            if opcao is None or opcao.pergunta_id != pergunta.id:
                raise ErroAuth(422, "Opção inválida.")
        return None, None, vistos
    opcao_id = item.get("opcao_id")
    opcao = db.get(OpcaoResposta, opcao_id) if opcao_id else None
    if opcao is None or opcao.pergunta_id != pergunta.id:
        raise ErroAuth(422, "Opção inválida.")
    return None, None, opcao.id
