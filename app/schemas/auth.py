from pydantic import BaseModel, Field


class LoginEntrada(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    senha: str = Field(min_length=1, max_length=200)


class SenhaNova(BaseModel):
    senha: str = Field(min_length=8, max_length=200)


class BootstrapEntrada(SenhaNova):
    nome: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=255)


class ConviteEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, max_length=255)
    papel: str
    projeto_id: str | None = None


class PrimeiroAcessoEntrada(SenhaNova):
    token: str = Field(min_length=10, max_length=200)


class RecuperarEntrada(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class RedefinirEntrada(SenhaNova):
    token: str = Field(min_length=10, max_length=200)


class RefreshEntrada(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)


class TokensSaida(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    painel: str


class UsuarioSaida(BaseModel):
    id: str
    nome: str
    email: str
    papel: str
    painel: str


class MensagemSaida(BaseModel):
    mensagem: str
    link_primeiro_acesso: str | None = None
