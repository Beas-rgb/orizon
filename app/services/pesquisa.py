"""Pesquisa. Clima não diz quem respondeu. Desempenho devolve a nota
só a quem tem o token. O órgão vê agregado, nunca a lista de pessoas.
"""

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tokens import novo_id
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


def _ciente(valor):
    if valor is None:
        return None
    if valor.tzinfo is None:
        from datetime import UTC

        return valor.replace(tzinfo=UTC)
    return valor


def _auditar(db: Session, acao: str, usuario_id: str) -> None:
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=usuario_id,
            acao=acao,
            criado_em=agora(),
        )
    )


def _papel(db: Session, usuario: Usuario, projeto_id: str) -> str | None:
    projeto = db.get(Projeto, projeto_id)
    if projeto is None or projeto.deleted_at is not None:
        return None
    if usuario.id == projeto.consultor_id:
        return "CONSULTOR"
    vinculo = db.scalar(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    return vinculo.papel if vinculo else None


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
    if _papel(db, consultor, projeto_id) != "CONSULTOR":
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
    papel = _papel(db, usuario, projeto_id)
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
    if _papel(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
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
    if _papel(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
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
    """Consultora/órgão do projeto ou funcionário vinculado. Sem vazar key."""
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    papel = _papel(db, usuario, pesquisa.projeto_id)
    if papel not in {"CONSULTOR", "ORGAO", "FUNCIONARIO"}:
        raise ErroAuth(404, "Pergunta não encontrada.")
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


def publicar(db: Session, consultor: Usuario, pesquisa_id: str) -> Pesquisa:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if _papel(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
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
        )
    db.commit()
    return pesquisa


def encerrar(db: Session, consultor: Usuario, pesquisa_id: str) -> Pesquisa:
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if _papel(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
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
    if _papel(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
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
    if _papel(db, consultor, projeto_id) != "CONSULTOR":
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
    if _papel(db, consultor, pesquisa.projeto_id) != "CONSULTOR":
        raise ErroAuth(404, "Pesquisa não encontrada.")
    if pesquisa.status != "PUBLICADA":
        raise ErroAuth(422, "Publique a pesquisa antes de gerar o link.")
    if quantidade < 1 or quantidade > 500:
        raise ErroAuth(
            422,
            "Gere até 500 links por vez. Pode repetir até cobrir todos.",
        )
    agora_ = agora()
    links: list[str] = []
    for _ in range(quantidade):
        token = str(uuid.uuid4())
        db.add(
            TokenResposta(
                id=novo_id(),
                pesquisa_id=pesquisa.id,
                setor_id=None,
                token=token,
                usado=False,
                expira_em=pesquisa.disponivel_ate,
                criado_em=agora_,
            )
        )
        links.append(token)
    _auditar(db, "TOKENS_GERADOS", consultor.id)
    db.commit()
    return links


def _token_convite(db: Session, token: str) -> TokenResposta:
    """Resolve o link de entrada. Não exige `usado` — o controle é o participante."""
    linha = db.scalar(select(TokenResposta).where(TokenResposta.token == token))
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
    if _papel(db, usuario, pesquisa.projeto_id) != "FUNCIONARIO":
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
        pessoal = TokenResposta(
            id=novo_id(),
            pesquisa_id=pesquisa.id,
            setor_id=None,
            token=str(uuid.uuid4()),
            usado=False,
            expira_em=pesquisa.disponivel_ate,
            criado_em=agora_,
        )
        db.add(pessoal)
        db.flush()
        participante.token_id = pessoal.id
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
                        token_id=linha.id,
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
                    token_id=linha.id,
                    pergunta_id=pergunta.id,
                    valor_texto=texto,
                    valor_numerico=numerico,
                    opcao_id=opcoes,
                    respondido_em=agora_,
                )
            )
    linha.usado = True
    linha.usado_em = agora_
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
    papel = _papel(db, usuario, pesquisa.projeto_id)
    if papel not in {"CONSULTOR", "ORGAO"}:
        raise ErroAuth(404, "Pesquisa não encontrada.")
    perguntas = db.scalars(
        select(Pergunta)
        .where(
            Pergunta.pesquisa_id == pesquisa.id,
            Pergunta.deleted_at.is_(None),
        )
        .order_by(Pergunta.ordem)
    ).all()
    saida = []
    for pergunta in perguntas:
        # Participantes únicos (token pessoal), não linhas de checkbox.
        total = db.scalar(
            select(func.count(func.distinct(Resposta.token_id))).where(
                Resposta.pergunta_id == pergunta.id
            )
        )
        media = db.scalar(
            select(func.avg(Resposta.valor_numerico)).where(
                Resposta.pergunta_id == pergunta.id,
                Resposta.valor_numerico.is_not(None),
            )
        )
        contagem_opcoes = None
        if pergunta.tipo in {"CHECKBOX", "MULTIPLA_ESCOLHA", "SIM_NAO"}:
            contagem_opcoes = []
            for opcao in opcoes_da(db, pergunta.id):
                qtd = db.scalar(
                    select(func.count(Resposta.id)).where(
                        Resposta.opcao_id == opcao.id
                    )
                )
                contagem_opcoes.append(
                    {
                        "opcao_id": opcao.id,
                        "texto": opcao.texto,
                        "total": int(qtd or 0),
                    }
                )
        saida.append(
            {
                "pergunta_id": pergunta.id,
                "texto": pergunta.texto,
                "tipo": pergunta.tipo,
                "respostas": int(total or 0),
                "media": float(media) if media is not None else None,
                "contagem_opcoes": contagem_opcoes,
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
