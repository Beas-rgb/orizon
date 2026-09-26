"""Lista e criação de projetos. Sem tela: o front só vai chamar isto.

Autorização: consultora cria e lista os dela. Órgão só vê projeto em que
foi vinculado. ID de outro cliente responde 404, não 403, para não
confirmar que o projeto existe.
"""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.routers._erro import chamar
from app.schemas.projeto import (
    CargoCriar,
    CargoSaida,
    ConfiguracaoAtualizar,
    ConfiguracaoSaida,
    EquipeSaida,
    ImportacaoConfirmarEntrada,
    ImportacaoConfirmarSaida,
    ImportacaoPreviaSaida,
    PerfilFuncionarioEntrada,
    PerfilFuncionarioSaida,
    ProjetoAtualizar,
    ProjetoCriar,
    ProjetoSaida,
    ReenviarFuncionarioEntrada,
    RotuloSaida,
    SetorCriar,
    SetorSaida,
)
from app.services.estrutura import (
    arvore_hierarquica,
    criar_cargo,
    definir_perfil_funcionario,
    listar_cargos,
    listar_perfis,
)
from app.services.importacao import (
    ImportacaoInvalida,
    confirmar_importacao,
    ler_arquivo,
    validar_linhas,
)
from app.services.projeto import (
    atualizar_configuracao,
    atualizar_projeto,
    criar_projeto,
    criar_setor,
    listar_equipe,
    listar_projetos,
    listar_rotulos,
    listar_setores,
    obter_configuracao,
    obter_projeto,
    reenviar_convite,
    reenviar_convite_funcionario,
    remover_setor,
)

router = APIRouter(prefix="/projetos", tags=["projetos"])


@router.get("/rotulos", response_model=list[RotuloSaida])
def rotulos(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[RotuloSaida]:
    """Rótulos da aba de projetos. Já nascem no banco, a tela não inventa."""
    if usuario.papel == "TI":
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    itens = listar_rotulos(db)
    return [
        RotuloSaida(id=item.id, codigo=item.codigo, nome=item.nome)
        for item in itens
    ]


@router.get("", response_model=list[ProjetoSaida])
def listar(
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
    limite: int = Query(50, ge=1, le=100),
    deslocamento: int = Query(0, ge=0),
) -> list[ProjetoSaida]:
    montados = chamar(
        lambda: listar_projetos(
            db, usuario, limite=limite, deslocamento=deslocamento
        )
    )
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
    montado = chamar(lambda: obter_projeto(db, usuario, projeto_id))
    return ProjetoSaida.model_validate(montado, from_attributes=True)


@router.post("", response_model=ProjetoSaida)
def criar(
    corpo: ProjetoCriar,
    background_tasks: BackgroundTasks,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ProjetoSaida:
    """Cria o projeto, puxa o órgão pelo CNPJ e envia o e-mail de acesso."""
    montado = chamar(
        lambda: criar_projeto(
            db,
            consultor,
            corpo.rotulo_id,
            corpo.cnpj,
            corpo.email_orgao,
            corpo.vinculo_tipo,
            corpo.vinculo_titulo,
            tarefas=background_tasks,
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
    montado = chamar(
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
) -> dict[str, str | None]:
    """Reenvia o convite se o órgão ainda não aceitou. Token antigo deixa de valer."""
    saida = chamar(lambda: reenviar_convite(db, consultor, projeto_id))
    return {
        "mensagem": "Convite reenviado.",
        "email": saida["email"],
        "link_primeiro_acesso": saida.get("link_primeiro_acesso"),
    }


@router.post("/{projeto_id}/reenviar-convite-funcionario")
def reenviar_funcionario(
    projeto_id: str,
    corpo: ReenviarFuncionarioEntrada,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    """Reenvia convite de funcionário pendente. Token antigo deixa de valer."""
    saida = chamar(
        lambda: reenviar_convite_funcionario(
            db, consultor, projeto_id, corpo.email
        )
    )
    return {
        "mensagem": "Convite reenviado.",
        "email": saida["email"],
        "link_primeiro_acesso": saida.get("link_primeiro_acesso"),
    }


@router.get("/{projeto_id}/equipe", response_model=list[EquipeSaida])
def equipe(
    projeto_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
    limite: int = Query(50, ge=1, le=100),
    deslocamento: int = Query(0, ge=0),
) -> list[EquipeSaida]:
    """Quem entra neste trabalho. Só a consultora dona. Sem token."""
    itens = chamar(
        lambda: listar_equipe(
            db, consultor, projeto_id, limite=limite, deslocamento=deslocamento
        )
    )
    return [EquipeSaida(**item) for item in itens]


@router.get("/{projeto_id}/setores", response_model=list[SetorSaida])
def setores(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[SetorSaida]:
    itens = chamar(lambda: listar_setores(db, usuario, projeto_id))
    return [SetorSaida(id=item.id, nome=item.nome) for item in itens]


@router.post("/{projeto_id}/setores", response_model=SetorSaida)
def criar_setor_rota(
    projeto_id: str,
    corpo: SetorCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> SetorSaida:
    setor = chamar(lambda: criar_setor(db, consultor, projeto_id, corpo.nome))
    return SetorSaida(id=setor.id, nome=setor.nome)


@router.delete("/{projeto_id}/setores/{setor_id}", status_code=204)
def apagar_setor(
    projeto_id: str,
    setor_id: str,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> None:
    chamar(lambda: remover_setor(db, consultor, projeto_id, setor_id))


@router.get("/{projeto_id}/cargos", response_model=list[CargoSaida])
def cargos(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[CargoSaida]:
    itens = chamar(lambda: listar_cargos(db, usuario, projeto_id))
    return [CargoSaida(id=item.id, nome=item.nome) for item in itens]


@router.post("/{projeto_id}/cargos", response_model=CargoSaida)
def criar_cargo_rota(
    projeto_id: str,
    corpo: CargoCriar,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> CargoSaida:
    cargo = chamar(lambda: criar_cargo(db, consultor, projeto_id, corpo.nome))
    return CargoSaida(id=cargo.id, nome=cargo.nome)


@router.get("/{projeto_id}/perfis", response_model=list[PerfilFuncionarioSaida])
def perfis(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[PerfilFuncionarioSaida]:
    itens = chamar(lambda: listar_perfis(db, usuario, projeto_id))
    return [
        PerfilFuncionarioSaida(
            usuario_id=item.usuario_id,
            setor_id=item.setor_id,
            cargo_id=item.cargo_id,
            superior_id=item.superior_id,
        )
        for item in itens
    ]


@router.put("/{projeto_id}/perfis", response_model=PerfilFuncionarioSaida)
def definir_perfil(
    projeto_id: str,
    corpo: PerfilFuncionarioEntrada,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> PerfilFuncionarioSaida:
    perfil = chamar(
        lambda: definir_perfil_funcionario(
            db,
            consultor,
            projeto_id,
            corpo.usuario_id,
            setor_id=corpo.setor_id,
            cargo_id=corpo.cargo_id,
            superior_id=corpo.superior_id,
        )
    )
    return PerfilFuncionarioSaida(
        usuario_id=perfil.usuario_id,
        setor_id=perfil.setor_id,
        cargo_id=perfil.cargo_id,
        superior_id=perfil.superior_id,
    )


@router.get("/{projeto_id}/arvore")
def arvore(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return chamar(lambda: arvore_hierarquica(db, usuario, projeto_id))


@router.post("/{projeto_id}/importar/previa", response_model=ImportacaoPreviaSaida)
def importar_previa(
    projeto_id: str,
    arquivo: UploadFile = File(...),
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ImportacaoPreviaSaida:
    """Lê o arquivo e devolve a prévia. Não grava nada."""
    from app.models.projeto import Projeto

    projeto = db.get(Projeto, projeto_id)
    if (
        projeto is None
        or projeto.deleted_at is not None
        or projeto.consultor_id != consultor.id
    ):
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    conteudo = arquivo.file.read()
    try:
        linhas = ler_arquivo(conteudo, arquivo.filename or "arquivo")
        previa = validar_linhas(db, projeto, linhas)
    except ImportacaoInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return ImportacaoPreviaSaida(
        total=previa.total,
        validos=previa.validos,
        invalidos=previa.invalidos,
        setores=previa.setores,
        cargos=previa.cargos,
        niveis=previa.niveis,
        duplicados=previa.duplicados,
        superiores_inexistentes=previa.superiores_inexistentes,
        linhas=[
            {
                "nome": linha.nome,
                "email": linha.email,
                "cargo": linha.cargo,
                "setor": linha.setor,
                "superior_email": linha.superior_email,
                "erros": linha.erros,
            }
            for linha in previa.linhas
        ],
    )


@router.post(
    "/{projeto_id}/importar/confirmar",
    response_model=ImportacaoConfirmarSaida,
)
def importar_confirmar(
    projeto_id: str,
    corpo: ImportacaoConfirmarEntrada,
    consultor: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ImportacaoConfirmarSaida:
    """Grava só as linhas válidas. Tudo numa transação."""
    from app.services.importacao import LinhaImportacao

    linhas = [
        LinhaImportacao(
            nome=str(linha.get("nome", "")),
            email=str(linha.get("email", "")),
            cargo=str(linha.get("cargo", "")),
            setor=str(linha.get("setor", "")),
            superior_email=str(linha.get("superior_email", "")),
            erros=[str(e) for e in linha.get("erros", [])],
        )
        for linha in corpo.linhas
    ]
    resultado = chamar(
        lambda: confirmar_importacao(db, consultor, projeto_id, linhas)
    )
    return ImportacaoConfirmarSaida(**resultado)


@router.get("/{projeto_id}/configuracao", response_model=ConfiguracaoSaida)
def ler_config(
    projeto_id: str,
    usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
) -> ConfiguracaoSaida:
    config = chamar(lambda: obter_configuracao(db, usuario, projeto_id))
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
    config = chamar(
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
