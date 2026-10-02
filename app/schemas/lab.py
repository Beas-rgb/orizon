"""Schemas do laboratório. Nenhum schema de entrada aceita tipo_conta."""

from pydantic import BaseModel, Field


class CenarioCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    tipo: str
    tamanho: int
    seed: int | None = None
    perfil: str = "ALEATORIO"
    com_senha: bool = False


class CenarioSaida(BaseModel):
    id: str
    nome: str
    tipo: str
    tamanho: int
    seed: int
    perfil: str
    status: str
    projeto_id: str | None
    progresso: int
    erro: str | None


class RespostasLabEntrada(BaseModel):
    perfil: str = "ALEATORIO"
    taxa: float = Field(ge=0, le=1, default=1.0)
    seed: int | None = None
