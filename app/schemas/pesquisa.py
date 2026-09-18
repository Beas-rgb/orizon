from pydantic import BaseModel, Field


class PesquisaCriar(BaseModel):
    titulo: str = Field(min_length=2, max_length=200)
    tipo: str
    descricao: str | None = None


class ModeloSalvar(BaseModel):
    nome: str = Field(min_length=2, max_length=200)


class PesquisaDeModelo(BaseModel):
    template_id: str
    titulo: str | None = None


class ModeloSaida(BaseModel):
    id: str
    nome: str
    tipo: str
    categoria: str


class OpcaoEntrada(BaseModel):
    texto: str = Field(min_length=1, max_length=200)


class PerguntaCriar(BaseModel):
    texto: str = Field(min_length=2)
    tipo: str
    obrigatoria: bool = True
    opcoes: list[OpcaoEntrada] = []


class PesquisaAtualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=2, max_length=200)
    descricao: str | None = None


class PerguntaAtualizar(BaseModel):
    texto: str | None = Field(default=None, min_length=2)
    tipo: str | None = None
    obrigatoria: bool | None = None
    opcoes: list[OpcaoEntrada] | None = None


class ReordenarPerguntas(BaseModel):
    pergunta_ids: list[str] = Field(min_length=1)


class RespostaEntrada(BaseModel):
    pergunta_id: str
    valor_texto: str | None = None
    valor_numerico: int | None = None
    opcao_id: str | None = None
    # CHECKBOX: várias opções. Demais tipos usam opcao_id.
    opcao_ids: list[str] = Field(default_factory=list)


class EnvioRespostas(BaseModel):
    respostas: list[RespostaEntrada]


class PesquisaSaida(BaseModel):
    id: str
    projeto_id: str
    titulo: str
    tipo: str
    status: str
    descricao: str | None


class PerguntaSaida(BaseModel):
    id: str
    pesquisa_id: str | None = None
    texto: str
    tipo: str
    obrigatoria: bool
    ordem: int
    opcoes: list[dict[str, str | int]]
    midia_tipo: str | None = None
    tem_midia: bool = False


class NotaSaida(BaseModel):
    tipo: str
    mensagem: str
    nota: float | None = None


class PainelPergunta(BaseModel):
    pergunta_id: str
    texto: str
    tipo: str
    # Participantes distintos (não linhas soltas de checkbox).
    respostas: int
    media: float | None = None
    contagem_opcoes: list[dict[str, str | int]] | None = None


class MinhaPesquisaSaida(BaseModel):
    """Item da tela Minhas pesquisas (funcionário)."""

    pesquisa_id: str
    projeto_id: str
    titulo: str
    tipo: str
    status_participacao: str
    disponivel_ate: str | None = None
    token: str | None = None


class ParticipanteStatusSaida(BaseModel):
    """Status do funcionário na pesquisa — sem conteúdo da resposta."""

    usuario_id: str
    nome: str
    email: str
    status: str
