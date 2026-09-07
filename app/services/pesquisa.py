"""Pesquisa. Clima não diz quem respondeu. Desempenho devolve a nota
só a quem tem o token. O órgão vê agregado, nunca a lista de pessoas.
"""

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tokens import novo_id
from app.models.auditoria import LogAuditoria
from app.models.base import agora
from app.models.configuracao import ConfiguracaoProjeto
from app.models.pesquisa import (
    OpcaoResposta,
    Pergunta,
    Pesquisa,
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
        copia = TemplatePergunta(
            id=novo_id(),
            template_id=modelo.id,
            texto=item.texto,
            tipo=item.tipo,
            obrigatoria=item.obrigatoria,
            ordem=item.ordem,
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
        pergunta = Pergunta(
            id=novo_id(),
            pesquisa_id=pesquisa.id,
            texto=item.texto,
            tipo=item.tipo,
            obrigatoria=item.obrigatoria,
            ordem=item.ordem,
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


def _token_aberto(db: Session, token: str) -> TokenResposta:
    linha = db.scalar(select(TokenResposta).where(TokenResposta.token == token))
    if linha is None or linha.usado:
        raise ErroAuth(404, "Link inválido ou já usado.")
    pesquisa = _pesquisa_viva(db, linha.pesquisa_id)
    if pesquisa.status != "PUBLICADA" or pesquisa.bloqueada:
        raise ErroAuth(404, "Link inválido ou já usado.")
    agora_ = agora()
    limite = _ciente(pesquisa.disponivel_ate)
    if limite and limite < agora_:
        raise ErroAuth(404, "Link inválido ou já usado.")
    return linha


def perguntas_do_token(db: Session, token: str) -> tuple[Pesquisa, list[Pergunta]]:
    linha = _token_aberto(db, token)
    pesquisa = _pesquisa_viva(db, linha.pesquisa_id)
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
) -> tuple[str, float | None]:
    linha = _token_aberto(db, token)
    pesquisa = _pesquisa_viva(db, linha.pesquisa_id)
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
    agora_ = agora()
    for item in itens:
        pergunta = perguntas.get(item["pergunta_id"])
        if pergunta is None:
            raise ErroAuth(422, "Pergunta inválida.")
        numerico, texto, opcao = _normalizar(db, pergunta, item)
        db.add(
            Resposta(
                id=novo_id(),
                token_id=linha.id,
                pergunta_id=pergunta.id,
                valor_texto=texto,
                valor_numerico=numerico,
                opcao_id=opcao,
                respondido_em=agora_,
            )
        )
    linha.usado = True
    linha.usado_em = agora_
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
    db.commit()
    if pesquisa.tipo == "DESEMPENHO":
        return pesquisa.tipo, _nota_do_token(db, linha.id)
    return pesquisa.tipo, None


def nota_do_token(db: Session, token: str) -> tuple[str, float | None]:
    linha = db.scalar(select(TokenResposta).where(TokenResposta.token == token))
    if linha is None or not linha.usado:
        raise ErroAuth(404, "Link inválido ou já usado.")
    pesquisa = _pesquisa_viva(db, linha.pesquisa_id)
    if pesquisa.tipo != "DESEMPENHO":
        return pesquisa.tipo, None
    return pesquisa.tipo, _nota_do_token(db, linha.id)


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
        total = db.scalar(
            select(func.count(Resposta.id)).where(Resposta.pergunta_id == pergunta.id)
        )
        media = db.scalar(
            select(func.avg(Resposta.valor_numerico)).where(
                Resposta.pergunta_id == pergunta.id,
                Resposta.valor_numerico.is_not(None),
            )
        )
        saida.append(
            {
                "pergunta_id": pergunta.id,
                "texto": pergunta.texto,
                "tipo": pergunta.tipo,
                "respostas": int(total or 0),
                "media": float(media) if media is not None else None,
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


def _normalizar(db: Session, pergunta: Pergunta, item: dict) -> tuple:
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
    opcao_id = item.get("opcao_id")
    opcao = db.get(OpcaoResposta, opcao_id) if opcao_id else None
    if opcao is None or opcao.pergunta_id != pergunta.id:
        raise ErroAuth(422, "Opção inválida.")
    return None, None, opcao.id
