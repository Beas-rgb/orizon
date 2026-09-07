from datetime import datetime

from pydantic import BaseModel


class NotificacaoSaida(BaseModel):
    id: str
    tipo: str
    titulo: str
    mensagem: str
    lida: bool
    projeto_id: str | None
    criado_em: datetime


class EntregaSaida(BaseModel):
    id: str
    canal: str
    destino: str
    assunto: str
    status: str
    referencia: str
    criado_em: datetime
