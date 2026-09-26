"""Pesquisa. O token é o link de entrada; quem responde é o funcionário
autenticado. O painel do órgão não devolve token nem nome.
"""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.routers._erro import chamar
from app.schemas.pesquisa import (
    EnvioRespostas,
    MinhaPesquisaSaida,
    ModeloSaida,
    ModeloSalvar,
    NotaSaida,
    PainelPergunta,
    ParticipantesSaida,
    ParticipanteStatusSaida,
    PerguntaAtualizar,
    PerguntaCriar,
    PerguntaSaida,
    PesquisaAtualizar,
    PesquisaConsultoraSaida,
    PesquisaCriar,
    PesquisaDeModelo,
    PesquisaSaida,
    ReordenarPerguntas,
)
from app.services.pesquisa import (
    adicionar_pergunta,
    anexar_midia_pergunta,
    atualizar_ciclo,
    baixar_midia_da_pesquisa,
    baixar_midia_pelo_token,
    baixar_midia_pergunta,
    calcular_resultado_avaliacao,
    criar_ciclo,
    criar_de_modelo,
    criar_pesquisa,
    editar_pergunta,
    editar_pesquisa,
    encerrar,
    excluir_pergunta,
    gerar_relacoes,
    gerar_tokens,
    listar_ciclos,
    listar_minhas_pesquisas,
    listar_modelos,
    listar_participantes_status,
    listar_perguntas_pesquisa,
    listar_pesquisas,
    listar_pesquisas_consultora,
    listar_relacoes,
    nota_da_pesquisa,
    nota_do_token,
    opcoes_da,
    painel,
    perguntas_da_pesquisa,
    perguntas_do_token,
    publicar,
    registrar_resposta_avaliacao,
    registrar_respostas,
    registrar_respostas_da_pesquisa,
    relacao_do_avaliador,
    remover_midia_pergunta,
    reordenar_perguntas,
    salvar_modelo,
)

router = APIRouter(tags=["pesquisas"])


def _saida(pesquisa) -> PesquisaSaida:
    return PesquisaSaida(
        id=pesquisa.id,
        projeto_id=pesquisa.projeto_id,
        titulo=pesquisa.titulo,
        tipo=pesquisa.tipo,
        status=pesquisa.status,
        descricao=pesquisa.descricao,
    )


def _ciclo_saida(ciclo) -> dict:
    return {
        "id": ciclo.id,
        "nome": ciclo.nome,
        "escopo": ciclo.escopo,
        "status": ciclo.status,
        "configuracao": ciclo.configuracao,
    }


@router.post("/projetos/{projeto_id}/pesquisas", response_model=PesquisaSaida)
def criar(
    projeto_id: str,
    corpo: PesquisaCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    pesquisa = chamar(
        lambda: criar_pesquisa(
            db,
            consultor,
            projeto_id,
            corpo.titulo,
            corpo.tipo,
            corpo.descricao,
        )
    )
    return _saida(pesquisa)


@router.get("/projetos/{projeto_id}/pesquisas", response_model=list[PesquisaSaida])
def listar(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PesquisaSaida]:
    itens = chamar(lambda: listar_pesquisas(db, usuario, projeto_id))
    return [_saida(item) for item in itens]


@router.get(
    "/consultora/pesquisas",
    response_model=list[PesquisaConsultoraSaida],
)
def listar_todas_consultora(
    organizacao_id: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    status: str | None = Query(default=None),
    ano: int | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PesquisaConsultoraSaida]:
    """Pesquisas de todos os trabalhos da consultora. Segurança no backend."""
    itens = chamar(
        lambda: listar_pesquisas_consultora(
            db,
            usuario,
            organizacao_id=organizacao_id,
            tipo=tipo,
            status=status,
            ano=ano,
            limite=limite,
            deslocamento=deslocamento,
        )
    )
    return [PesquisaConsultoraSaida(**item) for item in itens]


def _pergunta_saida(db: Session, pergunta) -> PerguntaSaida:
    opcoes = opcoes_da(db, pergunta.id)
    return PerguntaSaida(
        id=pergunta.id,
        pesquisa_id=pergunta.pesquisa_id,
        texto=pergunta.texto,
        tipo=pergunta.tipo,
        obrigatoria=pergunta.obrigatoria,
        ordem=pergunta.ordem,
        opcoes=[
            {"id": item.id, "texto": item.texto, "ordem": item.ordem}
            for item in opcoes
        ],
        midia_tipo=pergunta.midia_tipo,
        tem_midia=bool(pergunta.midia_key),
    )


@router.get("/eu/pesquisas", response_model=list[MinhaPesquisaSaida])
def minhas_pesquisas(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[MinhaPesquisaSaida]:
    """Minhas pesquisas do funcionário (PENDENTE / EM_ANDAMENTO / RESPONDIDA)."""
    return [
        MinhaPesquisaSaida(**item)
        for item in chamar(lambda: listar_minhas_pesquisas(db, usuario))
    ]


@router.get(
    "/eu/pesquisas/{pesquisa_id}/formulario",
    response_model=list[PerguntaSaida],
)
def formulario_por_pesquisa(
    pesquisa_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PerguntaSaida]:
    """Resposta autenticada sem token no link (Minhas pesquisas)."""
    _pesquisa, perguntas = chamar(
        lambda: perguntas_da_pesquisa(db, pesquisa_id, usuario)
    )
    return [_pergunta_saida(db, item) for item in perguntas]


@router.get("/eu/pesquisas/{pesquisa_id}/perguntas/{pergunta_id}/midia")
def midia_por_pesquisa(
    pesquisa_id: str,
    pergunta_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    conteudo, mime = chamar(
        lambda: baixar_midia_da_pesquisa(db, pesquisa_id, pergunta_id, usuario)
    )
    return Response(content=conteudo, media_type=mime)


@router.post("/eu/pesquisas/{pesquisa_id}/responder", response_model=NotaSaida)
def responder_por_pesquisa(
    pesquisa_id: str,
    corpo: EnvioRespostas,
    request: Request,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> NotaSaida:
    ip = request.client.host if request.client else None
    tipo, nota = chamar(
        lambda: registrar_respostas_da_pesquisa(
            db,
            pesquisa_id,
            [item.model_dump() for item in corpo.respostas],
            usuario,
            ip,
        )
    )
    if tipo != "DESEMPENHO":
        return NotaSaida(
            tipo=tipo,
            mensagem="Resposta registrada. Sua identidade não é mostrada.",
            nota=None,
        )
    return NotaSaida(
        tipo="DESEMPENHO",
        mensagem="Esta é a sua nota. O órgão vê só a média.",
        nota=nota,
    )


@router.get("/eu/pesquisas/{pesquisa_id}/nota", response_model=NotaSaida)
def nota_por_pesquisa(
    pesquisa_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> NotaSaida:
    tipo, valor = chamar(lambda: nota_da_pesquisa(db, pesquisa_id, usuario))
    if tipo != "DESEMPENHO":
        return NotaSaida(
            tipo=tipo,
            mensagem="Resposta registrada. Clima não devolve nota individual.",
            nota=None,
        )
    return NotaSaida(tipo=tipo, mensagem="Sua nota.", nota=valor)


@router.get(
    "/pesquisas/{pesquisa_id}/participantes",
    response_model=ParticipantesSaida,
)
def participantes(
    pesquisa_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
    limite: int = Query(default=50, ge=1, le=100),
    deslocamento: int = Query(default=0, ge=0),
) -> ParticipantesSaida:
    """CLIMA: só totais. Demais tipos: status nominal — sem conteúdo de resposta."""
    dados = chamar(
        lambda: listar_participantes_status(
            db,
            consultor,
            pesquisa_id,
            limite=limite,
            deslocamento=deslocamento,
        )
    )
    itens = None
    if dados.get("itens") is not None:
        itens = [ParticipanteStatusSaida(**item) for item in dados["itens"]]
    return ParticipantesSaida(
        agregado=bool(dados.get("agregado")),
        total=dados.get("total"),
        respondidas=dados.get("respondidas"),
        itens=itens,
    )


@router.get("/pesquisas/{pesquisa_id}/perguntas", response_model=list[PerguntaSaida])
def listar_perguntas(
    pesquisa_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PerguntaSaida]:
    """Estrutura da pesquisa para o editor/preview. Sem respostas."""
    return [
        _pergunta_saida(db, item)
        for item in chamar(
            lambda: listar_perguntas_pesquisa(db, consultor, pesquisa_id)
        )
    ]


@router.post("/pesquisas/{pesquisa_id}/perguntas", response_model=PerguntaSaida)
def pergunta(
    pesquisa_id: str,
    corpo: PerguntaCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PerguntaSaida:
    criada = chamar(
        lambda: adicionar_pergunta(
            db,
            consultor,
            pesquisa_id,
            corpo.texto,
            corpo.tipo,
            corpo.obrigatoria,
            [item.texto for item in corpo.opcoes],
        )
    )
    return _pergunta_saida(db, criada)


@router.patch("/pesquisas/{pesquisa_id}", response_model=PesquisaSaida)
def atualizar_pesquisa(
    pesquisa_id: str,
    corpo: PesquisaAtualizar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    campos = corpo.model_dump(exclude_unset=True)
    pesquisa = chamar(
        lambda: editar_pesquisa(
            db,
            consultor,
            pesquisa_id,
            campos.get("titulo"),
            campos.get("descricao"),
            descricao_enviada="descricao" in campos,
            config_calculo=campos.get("config_calculo"),
        )
    )
    return _saida(pesquisa)


@router.patch(
    "/pesquisas/{pesquisa_id}/perguntas/{pergunta_id}",
    response_model=PerguntaSaida,
)
def atualizar_pergunta(
    pesquisa_id: str,
    pergunta_id: str,
    corpo: PerguntaAtualizar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PerguntaSaida:
    campos = corpo.model_dump(exclude_unset=True)
    opcoes = None
    if "opcoes" in campos:
        opcoes = [item["texto"] for item in campos["opcoes"] or []]
    editada = chamar(
        lambda: editar_pergunta(
            db,
            consultor,
            pesquisa_id,
            pergunta_id,
            campos.get("texto"),
            campos.get("tipo"),
            campos.get("obrigatoria"),
            opcoes,
        )
    )
    return _pergunta_saida(db, editada)


@router.delete("/pesquisas/{pesquisa_id}/perguntas/{pergunta_id}")
def remover_pergunta(
    pesquisa_id: str,
    pergunta_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    chamar(lambda: excluir_pergunta(db, consultor, pesquisa_id, pergunta_id))
    return {"mensagem": "Pergunta removida."}


@router.post(
    "/pesquisas/{pesquisa_id}/perguntas/reordenar",
    response_model=list[PerguntaSaida],
)
def reordenar(
    pesquisa_id: str,
    corpo: ReordenarPerguntas,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PerguntaSaida]:
    itens = chamar(
        lambda: reordenar_perguntas(
            db, consultor, pesquisa_id, corpo.pergunta_ids
        )
    )
    return [_pergunta_saida(db, item) for item in itens]


@router.post(
    "/pesquisas/{pesquisa_id}/perguntas/{pergunta_id}/midia",
    response_model=PerguntaSaida,
)
async def upload_midia(
    pesquisa_id: str,
    pergunta_id: str,
    arquivo: UploadFile = File(...),
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PerguntaSaida:
    """Anexa foto/vídeo. MIME real pelos bytes; chave interna (não usa o nome)."""
    conteudo = await arquivo.read()
    pergunta = chamar(
        lambda: anexar_midia_pergunta(
            db, consultor, pesquisa_id, pergunta_id, conteudo
        )
    )
    return _pergunta_saida(db, pergunta)


@router.delete(
    "/pesquisas/{pesquisa_id}/perguntas/{pergunta_id}/midia",
    response_model=PerguntaSaida,
)
def apagar_midia(
    pesquisa_id: str,
    pergunta_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PerguntaSaida:
    pergunta = chamar(
        lambda: remover_midia_pergunta(db, consultor, pesquisa_id, pergunta_id)
    )
    return _pergunta_saida(db, pergunta)


@router.get("/pesquisas/{pesquisa_id}/perguntas/{pergunta_id}/midia")
def baixar_midia(
    pesquisa_id: str,
    pergunta_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    conteudo, mime = chamar(
        lambda: baixar_midia_pergunta(db, usuario, pesquisa_id, pergunta_id)
    )
    return Response(content=conteudo, media_type=mime)


@router.post("/pesquisas/{pesquisa_id}/encerrar", response_model=PesquisaSaida)
def encerrar_rota(
    pesquisa_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    """Fecha a pesquisa. O link deixa de aceitar resposta. O painel continua."""
    return _saida(chamar(lambda: encerrar(db, consultor, pesquisa_id)))


@router.post("/pesquisas/{pesquisa_id}/modelo", response_model=ModeloSaida)
def modelo(
    pesquisa_id: str,
    corpo: ModeloSalvar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ModeloSaida:
    """Copia a pesquisa para um modelo da consultora. Não vai para o órgão."""
    item = chamar(lambda: salvar_modelo(db, consultor, pesquisa_id, corpo.nome))
    return ModeloSaida(
        id=item.id,
        nome=item.nome,
        tipo=item.tipo,
        categoria=item.categoria,
    )


@router.get("/modelos", response_model=list[ModeloSaida])
def modelos(
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[ModeloSaida]:
    itens = chamar(lambda: listar_modelos(db, consultor))
    return [
        ModeloSaida(
            id=item.id,
            nome=item.nome,
            tipo=item.tipo,
            categoria=item.categoria,
        )
        for item in itens
    ]


@router.post("/projetos/{projeto_id}/pesquisas/de-modelo", response_model=PesquisaSaida)
def de_modelo(
    projeto_id: str,
    corpo: PesquisaDeModelo,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    """Abre um rascunho no projeto a partir do modelo. Não copia respostas."""
    pesquisa = chamar(
        lambda: criar_de_modelo(
            db,
            consultor,
            projeto_id,
            corpo.template_id,
            corpo.titulo,
        )
    )
    return _saida(pesquisa)


@router.post("/pesquisas/{pesquisa_id}/publicar", response_model=PesquisaSaida)
def publicar_rota(
    pesquisa_id: str,
    background_tasks: BackgroundTasks,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    return _saida(
        chamar(
            lambda: publicar(
                db, consultor, pesquisa_id, tarefas=background_tasks
            )
        )
    )

@router.post("/pesquisas/{pesquisa_id}/tokens")
def tokens(
    pesquisa_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
    quantidade: int = 1,
) -> dict[str, list[str]]:
    """A consultora recebe tokens e links React. Sem nome de quem responde."""
    from app.core.config import url_publica

    gerados = chamar(
        lambda: gerar_tokens(db, consultor, pesquisa_id, quantidade)
    )
    base = url_publica().rstrip("/")
    return {
        "tokens": gerados,
        "links": [f"{base}/responder/{token}" for token in gerados],
    }


@router.get("/pesquisas/{pesquisa_id}/painel", response_model=list[PainelPergunta])
def painel_rota(
    pesquisa_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PainelPergunta]:
    """Agregado. Sem token, sem nome, sem resposta individual."""
    linhas = chamar(lambda: painel(db, usuario, pesquisa_id))
    return [PainelPergunta(**linha) for linha in linhas]


@router.get("/responder/{token}", response_model=list[PerguntaSaida])
def formulario(
    token: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PerguntaSaida]:
    """Exige funcionário autenticado do projeto. Token só identifica a pesquisa."""
    _pesquisa, perguntas = chamar(
        lambda: perguntas_do_token(db, token, usuario)
    )
    return [_pergunta_saida(db, item) for item in perguntas]


@router.get("/responder/{token}/perguntas/{pergunta_id}/midia")
def midia_pelo_token(
    token: str,
    pergunta_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> Response:
    """Mídia da pergunta no fluxo de resposta (funcionário autenticado)."""
    conteudo, mime = chamar(
        lambda: baixar_midia_pelo_token(db, token, pergunta_id, usuario)
    )
    return Response(content=conteudo, media_type=mime)


@router.post("/responder/{token}", response_model=NotaSaida)
def responder(
    token: str,
    corpo: EnvioRespostas,
    request: Request,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> NotaSaida:
    ip = request.client.host if request.client else None
    tipo, nota = chamar(
        lambda: registrar_respostas(
            db,
            token,
            [item.model_dump() for item in corpo.respostas],
            usuario,
            ip,
        )
    )
    if tipo != "DESEMPENHO":
        return NotaSaida(
            tipo=tipo,
            mensagem="Resposta registrada. Sua identidade não é mostrada.",
            nota=None,
        )
    return NotaSaida(
        tipo="DESEMPENHO",
        mensagem="Esta é a sua nota. O órgão vê só a média.",
        nota=nota,
    )


@router.post("/projetos/{projeto_id}/ciclos")
def criar_ciclo_rota(
    projeto_id: str,
    corpo: dict,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict:
    ciclo = chamar(
        lambda: criar_ciclo(
            db,
            consultor,
            projeto_id,
            corpo.get("nome", ""),
            escopo=corpo.get("escopo", "ORGANIZACAO"),
            configuracao=corpo.get("configuracao"),
        )
    )
    return _ciclo_saida(ciclo)


@router.patch("/ciclos/{ciclo_id}")
def atualizar_ciclo_rota(
    ciclo_id: str,
    corpo: dict,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict:
    ciclo = chamar(
        lambda: atualizar_ciclo(
            db,
            consultor,
            ciclo_id,
            nome=corpo.get("nome"),
            escopo=corpo.get("escopo"),
            configuracao=corpo.get("configuracao"),
        )
    )
    return _ciclo_saida(ciclo)


@router.get("/projetos/{projeto_id}/ciclos")
def listar_ciclos_rota(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[dict]:
    itens = chamar(lambda: listar_ciclos(db, usuario, projeto_id))
    return [_ciclo_saida(item) for item in itens]


@router.post("/ciclos/{ciclo_id}/gerar-relacoes")
def gerar_relacoes_rota(
    ciclo_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict:
    return chamar(lambda: gerar_relacoes(db, consultor, ciclo_id))


@router.get("/ciclos/{ciclo_id}/relacoes")
def listar_relacoes_rota(
    ciclo_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[dict]:
    itens = chamar(lambda: listar_relacoes(db, usuario, ciclo_id))
    nomes: dict[str, str] = {}
    for item in itens:
        for uid in (item.avaliador_id, item.avaliado_id):
            if uid not in nomes:
                pessoa = db.get(Usuario, uid)
                nomes[uid] = pessoa.nome if pessoa else ""
    return [
        {
            "id": item.id,
            "avaliador_id": item.avaliador_id,
            "avaliado_id": item.avaliado_id,
            "avaliador_nome": nomes.get(item.avaliador_id, ""),
            "avaliado_nome": nomes.get(item.avaliado_id, ""),
            "tipo_relacao": item.tipo_relacao,
            "peso": item.peso,
            "status": item.status,
        }
        for item in itens
    ]


@router.get("/ciclos/{ciclo_id}/relacao/{avaliado_id}")
def relacao_rota(
    ciclo_id: str,
    avaliado_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict:
    relacao = chamar(lambda: relacao_do_avaliador(db, usuario, ciclo_id, avaliado_id))
    return {
        "id": relacao.id,
        "avaliador_id": relacao.avaliador_id,
        "avaliado_id": relacao.avaliado_id,
        "tipo_relacao": relacao.tipo_relacao,
        "peso": relacao.peso,
        "status": relacao.status,
    }


@router.get("/ciclos/{ciclo_id}/resultado/{avaliado_id}")
def resultado_rota(
    ciclo_id: str,
    avaliado_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict:
    return chamar(
        lambda: calcular_resultado_avaliacao(db, usuario, ciclo_id, avaliado_id)
    )


@router.post("/relacionamentos/{relacionamento_id}/respostas")
def registrar_resposta_avaliacao_rota(
    relacionamento_id: str,
    corpo: dict,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict:
    nota = corpo.get("valor_numerico")
    if nota is not None and not isinstance(nota, int):
        raise HTTPException(status_code=422, detail="Nota inválida.")
    resposta = chamar(
        lambda: registrar_resposta_avaliacao(
            db,
            usuario,
            relacionamento_id,
            str(corpo.get("pergunta_id") or ""),
            valor_numerico=nota,
            valor_texto=corpo.get("valor_texto"),
            opcao_id=corpo.get("opcao_id"),
        )
    )
    return {
        "id": resposta.id,
        "relacionamento_id": resposta.relacionamento_id,
        "pergunta_id": resposta.pergunta_id,
        "valor_numerico": resposta.valor_numerico,
    }


@router.get("/responder/{token}/nota", response_model=NotaSaida)
def nota(
    token: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> NotaSaida:
    tipo, valor = chamar(lambda: nota_do_token(db, token, usuario))
    if tipo != "DESEMPENHO":
        return NotaSaida(
            tipo=tipo,
            mensagem="Resposta registrada. Clima não devolve nota individual.",
            nota=None,
        )
    return NotaSaida(tipo=tipo, mensagem="Sua nota.", nota=valor)
