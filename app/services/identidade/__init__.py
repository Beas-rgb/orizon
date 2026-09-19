"""Regras de identidade. A rota só chama daqui.

Ataques que este módulo corta:
- força bruta no login: 3 erros gravam bloqueio de 5 minutos no banco
- senha no e-mail: o convite e a recuperação levam só um token de uso único
- enumeração no recuperar: a resposta é a mesma se o e-mail existe ou não
- reuso de token: o hash é marcado como usado e as sessões antigas caem
"""

from .auth import (
    bootstrap,
    garantir_admin,
    login,
    primeiro_acesso,
    recuperar_senha,
    redefinir_senha,
    refresh,
    sair,
)
from .convites import criar_convite
from .erros import (
    MSG_CREDENCIAL,
    MSG_ESPERA,
    MSG_RECUPERAR,
    MSG_TOKEN,
    PAINEIS,
    PAPEIS,
    ErroAuth,
    email_acesso,
    limpar_falhas,
    painel_de,
    registrar_falha,
    segundos_bloqueio,
    settings,
)
from .pedidos import (
    autorizar_pedido,
    diagnostico,
    listar_consultores,
    listar_pedidos,
    pedir_conta_consultora,
    reenviar_primeiro_acesso_consultora,
)

__all__ = [
    "MSG_CREDENCIAL",
    "MSG_ESPERA",
    "MSG_RECUPERAR",
    "MSG_TOKEN",
    "PAPEIS",
    "PAINEIS",
    "ErroAuth",
    "autorizar_pedido",
    "bootstrap",
    "criar_convite",
    "diagnostico",
    "email_acesso",
    "garantir_admin",
    "limpar_falhas",
    "listar_consultores",
    "listar_pedidos",
    "login",
    "painel_de",
    "pedir_conta_consultora",
    "primeiro_acesso",
    "recuperar_senha",
    "redefinir_senha",
    "reenviar_primeiro_acesso_consultora",
    "refresh",
    "registrar_falha",
    "sair",
    "segundos_bloqueio",
    "settings",
]
