"""Pesquisa. Sem tela. O token é o segredo de quem responde.

O painel do órgão não devolve token nem nome. Clima não devolve nota
individual. Desempenho devolve a nota só para quem apresenta o token.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.schemas.pesquisa import (
    EnvioRespostas,
    ModeloSaida,
    ModeloSalvar,
    NotaSaida,
    PainelPergunta,
    PerguntaCriar,
    PerguntaSaida,
    PesquisaCriar,
    PesquisaDeModelo,
    PesquisaSaida,
)
from app.services.identidade import ErroAuth
from app.services.pesquisa import (
    adicionar_pergunta,
    criar_de_modelo,
    criar_pesquisa,
    encerrar,
    gerar_tokens,
    listar_modelos,
    listar_pesquisas,
    nota_do_token,
    opcoes_da,
    painel,
    perguntas_do_token,
    publicar,
    registrar_respostas,
    salvar_modelo,
)

router = APIRouter(tags=["pesquisas"])


def _chamar(acao):
    try:
        return acao()
    except ErroAuth as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalhe) from None


def _saida(pesquisa) -> PesquisaSaida:
    return PesquisaSaida(
        id=pesquisa.id,
        projeto_id=pesquisa.projeto_id,
        titulo=pesquisa.titulo,
        tipo=pesquisa.tipo,
        status=pesquisa.status,
        descricao=pesquisa.descricao,
    )


@router.post("/projetos/{projeto_id}/pesquisas", response_model=PesquisaSaida)
def criar(
    projeto_id: str,
    corpo: PesquisaCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    pesquisa = _chamar(
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
    itens = _chamar(lambda: listar_pesquisas(db, usuario, projeto_id))
    return [_saida(item) for item in itens]


@router.post("/pesquisas/{pesquisa_id}/perguntas", response_model=PerguntaSaida)
def pergunta(
    pesquisa_id: str,
    corpo: PerguntaCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PerguntaSaida:
    criada = _chamar(
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
    opcoes = opcoes_da(db, criada.id)
    return PerguntaSaida(
        id=criada.id,
        texto=criada.texto,
        tipo=criada.tipo,
        obrigatoria=criada.obrigatoria,
        ordem=criada.ordem,
        opcoes=[
            {"id": item.id, "texto": item.texto, "ordem": item.ordem}
            for item in opcoes
        ],
    )


@router.post("/pesquisas/{pesquisa_id}/encerrar", response_model=PesquisaSaida)
def encerrar_rota(
    pesquisa_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    """Fecha a pesquisa. O link deixa de aceitar resposta. O painel continua."""
    return _saida(_chamar(lambda: encerrar(db, consultor, pesquisa_id)))


@router.post("/pesquisas/{pesquisa_id}/modelo", response_model=ModeloSaida)
def modelo(
    pesquisa_id: str,
    corpo: ModeloSalvar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ModeloSaida:
    """Copia a pesquisa para um modelo da consultora. Não vai para o órgão."""
    item = _chamar(lambda: salvar_modelo(db, consultor, pesquisa_id, corpo.nome))
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
    itens = _chamar(lambda: listar_modelos(db, consultor))
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
    pesquisa = _chamar(
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
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PesquisaSaida:
    return _saida(_chamar(lambda: publicar(db, consultor, pesquisa_id)))


@router.post("/pesquisas/{pesquisa_id}/tokens")
def tokens(
    pesquisa_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
    quantidade: int = 1,
) -> dict[str, list[str]]:
    """A consultora recebe os links. O nome de quem vai responder não é gravado."""
    links = _chamar(lambda: gerar_tokens(db, consultor, pesquisa_id, quantidade))
    return {"tokens": links}


@router.get("/pesquisas/{pesquisa_id}/painel", response_model=list[PainelPergunta])
def painel_rota(
    pesquisa_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PainelPergunta]:
    """Agregado. Sem token, sem nome, sem resposta individual."""
    linhas = _chamar(lambda: painel(db, usuario, pesquisa_id))
    return [PainelPergunta(**linha) for linha in linhas]


@router.get("/responder/{token}", response_model=list[PerguntaSaida])
def formulario(token: str, db: Session = Depends(get_db)) -> list[PerguntaSaida]:
    _pesquisa, perguntas = _chamar(lambda: perguntas_do_token(db, token))
    saida = []
    for item in perguntas:
        opcoes = opcoes_da(db, item.id)
        saida.append(
            PerguntaSaida(
                id=item.id,
                texto=item.texto,
                tipo=item.tipo,
                obrigatoria=item.obrigatoria,
                ordem=item.ordem,
                opcoes=[
                    {"id": opcao.id, "texto": opcao.texto, "ordem": opcao.ordem}
                    for opcao in opcoes
                ],
            )
        )
    return saida


@router.post("/responder/{token}", response_model=NotaSaida)
def responder(
    token: str,
    corpo: EnvioRespostas,
    db: Session = Depends(get_db),
) -> NotaSaida:
    tipo, nota = _chamar(
        lambda: registrar_respostas(
            db,
            token,
            [item.model_dump() for item in corpo.respostas],
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


@router.get("/responder/{token}/nota", response_model=NotaSaida)
def nota(token: str, db: Session = Depends(get_db)) -> NotaSaida:
    tipo, valor = _chamar(lambda: nota_do_token(db, token))
    if tipo != "DESEMPENHO":
        return NotaSaida(
            tipo=tipo,
            mensagem="Resposta registrada. Clima não devolve nota individual.",
            nota=None,
        )
    return NotaSaida(tipo=tipo, mensagem="Sua nota.", nota=valor)
