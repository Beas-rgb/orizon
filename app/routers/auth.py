"""Rotas de identidade. Sem HTML: o cliente fala só com estes endpoints.

Autorização: login, primeiro acesso, recuperar e redefinir são públicos
(o segredo é a senha ou o token). Convite exige consultora autenticada.
Nenhuma rota devolve senha, hash ou token de e-mail.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.schemas.auth import (
    BootstrapEntrada,
    ConviteEntrada,
    LoginEntrada,
    MensagemSaida,
    PrimeiroAcessoEntrada,
    RecuperarEntrada,
    RedefinirEntrada,
    RefreshEntrada,
    TokensSaida,
    UsuarioSaida,
)
from app.services.identidade import (
    MSG_RECUPERAR,
    ErroAuth,
    bootstrap,
    criar_convite,
    login,
    painel_de,
    primeiro_acesso,
    recuperar_senha,
    redefinir_senha,
    refresh,
    sair,
)

router = APIRouter(prefix="/auth", tags=["identidade"])


def _chamar(acao) -> object:
    try:
        return acao()
    except ErroAuth as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalhe) from None


@router.post("/bootstrap", response_model=TokensSaida)
def cadastrar_inicial(
    corpo: BootstrapEntrada,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Cria a primeira consultora. Só funciona com a tabela de usuários vazia."""
    return _chamar(lambda: bootstrap(db, corpo.nome, corpo.email, corpo.senha))


@router.post("/login", response_model=TokensSaida)
def entrar(corpo: LoginEntrada, db: Session = Depends(get_db)) -> dict[str, str]:
    """Login. 3 senhas erradas no mesmo e-mail bloqueiam por 5 minutos."""
    return _chamar(lambda: login(db, corpo.email, corpo.senha))


@router.post("/refresh", response_model=TokensSaida)
def renovar(corpo: RefreshEntrada, db: Session = Depends(get_db)) -> dict[str, str]:
    return _chamar(lambda: refresh(db, corpo.refresh_token))


@router.post("/sair", response_model=MensagemSaida)
def encerrar(corpo: RefreshEntrada, db: Session = Depends(get_db)) -> MensagemSaida:
    sair(db, corpo.refresh_token)
    return MensagemSaida(mensagem="Sessão encerrada.")


@router.get("/eu", response_model=UsuarioSaida)
def eu(usuario: Usuario = Depends(usuario_atual)) -> UsuarioSaida:
    return UsuarioSaida(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papel=usuario.papel,
        painel=painel_de(usuario.papel),
    )


@router.post("/convites", response_model=MensagemSaida)
def convidar(
    corpo: ConviteEntrada,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> MensagemSaida:
    """Convite. O e-mail leva o token de primeiro acesso, nunca uma senha."""
    _chamar(
        lambda: criar_convite(
            db,
            consultor,
            corpo.nome,
            corpo.email,
            corpo.papel,
            corpo.projeto_id,
        )
    )
    return MensagemSaida(mensagem="Convite registrado. O destinatário define a senha.")


@router.post("/primeiro-acesso", response_model=TokensSaida)
def ativar(
    corpo: PrimeiroAcessoEntrada,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    return _chamar(lambda: primeiro_acesso(db, corpo.token, corpo.senha))


@router.post("/recuperar-senha", response_model=MensagemSaida)
def pedir_redefinicao(
    corpo: RecuperarEntrada,
    db: Session = Depends(get_db),
) -> MensagemSaida:
    """Pedido ligado ao e-mail de acesso. A resposta não diz se a conta existe."""
    _chamar(lambda: recuperar_senha(db, corpo.email))
    return MensagemSaida(mensagem=MSG_RECUPERAR)


@router.post("/redefinir-senha", response_model=MensagemSaida)
def gravar_senha_nova(
    corpo: RedefinirEntrada,
    db: Session = Depends(get_db),
) -> MensagemSaida:
    _chamar(lambda: redefinir_senha(db, corpo.token, corpo.senha))
    return MensagemSaida(mensagem="Senha redefinida. Entre de novo com a senha nova.")
