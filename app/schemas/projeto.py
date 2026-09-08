from pydantic import BaseModel, ConfigDict, Field


class ProjetoCriar(BaseModel):
    rotulo_id: str = Field(min_length=1, max_length=36)
    cnpj: str = Field(min_length=14, max_length=18)
    email_orgao: str = Field(min_length=3, max_length=255)
    vinculo_tipo: str
    vinculo_titulo: str = Field(min_length=2, max_length=200)


class RotuloSaida(BaseModel):
    id: str
    codigo: str
    nome: str


class ProjetoAtualizar(BaseModel):
    estado: str | None = None
    vinculo_titulo: str | None = Field(default=None, min_length=2, max_length=200)


class SetorCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=120)


class SetorSaida(BaseModel):
    id: str
    nome: str


class EquipeSaida(BaseModel):
    nome: str
    email: str
    papel: str
    situacao: str


class ConfiguracaoSaida(BaseModel):
    pesquisas_habilitadas: bool
    ia_modo: str


class ConfiguracaoAtualizar(BaseModel):
    pesquisas_habilitadas: bool


class ProjetoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rotulo_id: str
    rotulo: str
    estado: str
    cnpj: str
    razao_social: str
    nome_fantasia: str | None
    email_orgao: str
    vinculo_tipo: str
    vinculo_titulo: str
    convite_entrega: str
