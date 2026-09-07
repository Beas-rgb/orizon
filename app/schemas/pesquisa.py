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


class RespostaEntrada(BaseModel):
    pergunta_id: str
    valor_texto: str | None = None
    valor_numerico: int | None = None
    opcao_id: str | None = None


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
    texto: str
    tipo: str
    obrigatoria: bool
    ordem: int
    opcoes: list[dict[str, str | int]]


class NotaSaida(BaseModel):
    tipo: str
    mensagem: str
    nota: float | None = None


class PainelPergunta(BaseModel):
    pergunta_id: str
    texto: str
    tipo: str
    respostas: int
    media: float | None = None
