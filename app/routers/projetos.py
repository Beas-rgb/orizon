"""Lista e criação de projetos. Sem tela: o front só vai chamar isto.

Autorização: consultora cria e lista os dela. Órgão só vê projeto em que
foi vinculado. ID de outro cliente responde 404, não 403, para não
confirmar que o projeto existe.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.schemas.projeto import (
    ConfiguracaoAtualizar,
    ConfiguracaoSaida,
    ProjetoAtualizar,
    ProjetoCriar,
    ProjetoSaida,
    RotuloSaida,
    SetorCriar,
    SetorSaida,
)
from app.services.identidade import ErroAuth
from app.services.projeto import (
    atualizar_configuracao,
    atualizar_projeto,
    criar_projeto,
    criar_setor,
    listar_projetos,
    listar_rotulos,
    listar_setores,
    obter_configuracao,
    obter_projeto,
    reenviar_convite,
    remover_setor,
)

router = APIRouter(prefix="/projetos", tags=["projetos"])


def _chamar(acao):
    try:
        return acao()
    except ErroAuth as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detalhe) from None


@router.get("/rotulos", response_model=list[RotuloSaida])
def rotulos(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[RotuloSaida]:
    """Rótulos da aba de projetos. Já nascem no banco, a tela não inventa."""
    if usuario.papel == "TI":
        raise HTTPException(status_code=403, detail="Sem acesso a projetos.")
    itens = listar_rotulos(db)
    return [
        RotuloSaida(id=item.id, codigo=item.codigo, nome=item.nome)
        for item in itens
    ]


@router.get("", response_model=list[ProjetoSaida])
def listar(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[ProjetoSaida]:
    montados = _chamar(lambda: listar_projetos(db, usuario))
    return [
        ProjetoSaida.model_validate(item, from_attributes=True)
        for item in montados
    ]


@router.get("/{projeto_id}", response_model=ProjetoSaida)
def detalhe(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ProjetoSaida:
    montado = _chamar(lambda: obter_projeto(db, usuario, projeto_id))
    return ProjetoSaida.model_validate(montado, from_attributes=True)


@router.post("", response_model=ProjetoSaida)
def criar(
    corpo: ProjetoCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ProjetoSaida:
    """Cria o projeto, puxa o órgão pelo CNPJ e envia o e-mail de acesso."""
    montado = _chamar(
        lambda: criar_projeto(
            db,
            consultor,
            corpo.rotulo_id,
            corpo.cnpj,
            corpo.email_orgao,
            corpo.vinculo_tipo,
            corpo.vinculo_titulo,
        )
    )
    return ProjetoSaida.model_validate(montado, from_attributes=True)


@router.patch("/{projeto_id}", response_model=ProjetoSaida)
def atualizar(
    projeto_id: str,
    corpo: ProjetoAtualizar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ProjetoSaida:
    """Só a consultora dona altera estado ou título. Órgão recebe 404."""
    montado = _chamar(
        lambda: atualizar_projeto(
            db,
            consultor,
            projeto_id,
            corpo.estado,
            corpo.vinculo_titulo,
        )
    )
    return ProjetoSaida.model_validate(montado, from_attributes=True)


@router.post("/{projeto_id}/reenviar-convite")
def reenviar(
    projeto_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Reenvia o convite se o órgão ainda não aceitou. Token antigo deixa de valer."""
    email = _chamar(lambda: reenviar_convite(db, consultor, projeto_id))
    return {"mensagem": "Convite reenviado.", "email": email}


@router.get("/{projeto_id}/setores", response_model=list[SetorSaida])
def setores(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[SetorSaida]:
    itens = _chamar(lambda: listar_setores(db, usuario, projeto_id))
    return [SetorSaida(id=item.id, nome=item.nome) for item in itens]


@router.post("/{projeto_id}/setores", response_model=SetorSaida)
def criar_setor_rota(
    projeto_id: str,
    corpo: SetorCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> SetorSaida:
    setor = _chamar(lambda: criar_setor(db, consultor, projeto_id, corpo.nome))
    return SetorSaida(id=setor.id, nome=setor.nome)


@router.delete("/{projeto_id}/setores/{setor_id}", status_code=204)
def apagar_setor(
    projeto_id: str,
    setor_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> None:
    _chamar(lambda: remover_setor(db, consultor, projeto_id, setor_id))


@router.get("/{projeto_id}/configuracao", response_model=ConfiguracaoSaida)
def ler_config(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ConfiguracaoSaida:
    config = _chamar(lambda: obter_configuracao(db, usuario, projeto_id))
    return ConfiguracaoSaida(
        pesquisas_habilitadas=config.pesquisas_habilitadas,
        ia_modo=config.ia_modo,
    )


@router.patch("/{projeto_id}/configuracao", response_model=ConfiguracaoSaida)
def gravar_config(
    projeto_id: str,
    corpo: ConfiguracaoAtualizar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ConfiguracaoSaida:
    """Liga ou desliga pesquisas. A IA permanece DESATIVADA."""
    config = _chamar(
        lambda: atualizar_configuracao(
            db,
            consultor,
            projeto_id,
            corpo.pesquisas_habilitadas,
        )
    )
    return ConfiguracaoSaida(
        pesquisas_habilitadas=config.pesquisas_habilitadas,
        ia_modo=config.ia_modo,
    )
