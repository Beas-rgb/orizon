"""Tokens, formulário, registro de respostas e notas."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.autorizacao import papel_no_projeto
from app.core.tokens import hash_token, novo_id
from app.models.base import agora
from app.models.controle_acesso import ControleAcesso
from app.models.pesquisa import (
    OpcaoResposta,
    Pergunta,
    Pesquisa,
    PesquisaParticipante,
    Resposta,
    TokenResposta,
)
from app.models.projeto import Projeto
from app.models.usuario import Usuario
from app.services.auditoria import registrar as _auditar
from app.services.identidade import ErroAuth
from app.services.pesquisa.comum import (
    RESPONDER_JANELA_MINUTOS,
    RESPONDER_MAX_TENTATIVAS,
    TIPOS_ANONIMOS,
    _ciente,
    _pesquisa_viva,
)
from app.services.pesquisa.crud import _criar_token_resposta


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


def _exigir_pesquisa_aberta(db: Session, pesquisa_id: str) -> Pesquisa:
    """PUBLICADA, não bloqueada, dentro do prazo — senão 404 genérico."""
    pesquisa = _pesquisa_viva(db, pesquisa_id)
    if pesquisa.status != "PUBLICADA" or pesquisa.bloqueada:
        raise ErroAuth(404, "Link inválido ou já usado.")
    limite = _ciente(pesquisa.disponivel_ate)
    if limite and limite < agora():
        raise ErroAuth(404, "Link inválido ou já usado.")
    return pesquisa


def _listar_perguntas_ordenadas(db: Session, pesquisa_id: str) -> list[Pergunta]:
    return list(
        db.scalars(
            select(Pergunta)
            .where(
                Pergunta.pesquisa_id == pesquisa_id,
                Pergunta.deleted_at.is_(None),
            )
            .order_by(Pergunta.ordem)
        ).all()
    )


def perguntas_do_token(
    db: Session,
    token: str,
    usuario: Usuario,
) -> tuple[Pesquisa, list[Pergunta]]:
    convite = _token_convite(db, token)
    pesquisa = _pesquisa_viva(db, convite.pesquisa_id)
    _participante_da_pesquisa(db, usuario, pesquisa, para_envio=False)
    db.commit()
    return pesquisa, _listar_perguntas_ordenadas(db, pesquisa.id)


def perguntas_da_pesquisa(
    db: Session,
    pesquisa_id: str,
    usuario: Usuario,
) -> tuple[Pesquisa, list[Pergunta]]:
    """Formulário pelo ID (Minhas pesquisas). Sem token no banco."""
    pesquisa = _exigir_pesquisa_aberta(db, pesquisa_id)
    _participante_da_pesquisa(db, usuario, pesquisa, para_envio=False)
    db.commit()
    return pesquisa, _listar_perguntas_ordenadas(db, pesquisa.id)


def registrar_respostas(
    db: Session,
    token: str,
    itens: list[dict],
    usuario: Usuario,
    ip: str | None = None,
) -> tuple[str, float | None]:
    convite = _token_convite(db, token)
    pesquisa = _pesquisa_viva(db, convite.pesquisa_id)
    return _registrar_respostas_em(db, pesquisa, itens, usuario, ip)


def registrar_respostas_da_pesquisa(
    db: Session,
    pesquisa_id: str,
    itens: list[dict],
    usuario: Usuario,
    ip: str | None = None,
) -> tuple[str, float | None]:
    pesquisa = _exigir_pesquisa_aberta(db, pesquisa_id)
    return _registrar_respostas_em(db, pesquisa, itens, usuario, ip)


def _registrar_respostas_em(
    db: Session,
    pesquisa: Pesquisa,
    itens: list[dict],
    usuario: Usuario,
    ip: str | None = None,
) -> tuple[str, float | None]:
    _rate_limit_responder(db, usuario.id, ip)
    # Persiste a contagem mesmo se o envio falhar depois (422) e der rollback.
    db.commit()
    participante = _participante_da_pesquisa(
        db, usuario, pesquisa, para_envio=True
    )
    # Trava o participante para o envio. Outro POST simultâneo espera ou falha.
    db.refresh(participante, with_for_update=True)
    if participante.status == "RESPONDIDA":
        raise ErroAuth(409, "Você já respondeu esta pesquisa.")
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
    return nota_da_pesquisa(db, convite.pesquisa_id, usuario)


def nota_da_pesquisa(
    db: Session,
    pesquisa_id: str,
    usuario: Usuario,
) -> tuple[str, float | None]:
    pesquisa = _exigir_pesquisa_aberta(db, pesquisa_id)
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
