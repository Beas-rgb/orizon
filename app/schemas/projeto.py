import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjetoCriar(BaseModel):
    rotulo_id: str = Field(min_length=1, max_length=36)
    # Aceita máscara (XX.XXX.XXX/XXXX-XX); normaliza antes de validar tamanho.
    cnpj: str = Field(min_length=14, max_length=18)
    email_orgao: str = Field(min_length=3, max_length=255)
    vinculo_tipo: str
    vinculo_titulo: str = Field(min_length=2, max_length=200)

    @field_validator("cnpj", mode="before")
    @classmethod
    def _cnpj_limpo(cls, valor: object) -> object:
        if not isinstance(valor, str):
            return valor
        # Remove pontuação; sobram 14 caracteres (numérico ou alfanumérico).
        limpo = re.sub(r"[^0-9A-Za-z]", "", valor).upper()
        return limpo

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
    onboarding_estado: str = "convite_pendente"
    convite_motivo: str | None = None
