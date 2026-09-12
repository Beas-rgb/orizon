"""Criação e lista de projetos.

A tela futura só lista e envia o formulário. A regra fica aqui:
rótulo vem do banco, nome do órgão vem do CNPJ, e-mail do órgão recebe
o convite. Sem linha em projeto_usuarios, o ID do projeto não abre nada.
"""

from datetime import UTC, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tokens import hash_token, novo_id, novo_token_opaco
from app.integrations.cnpj import (
    CnpjIndisponivel,
    CnpjInvalido,
    CnpjNaoEncontrado,
    DadosCnpj,
    buscar,
)
from app.models.auditoria import LogAuditoria
from app.models.base import agora
from app.models.configuracao import ConfiguracaoProjeto
from app.models.convite import Convite
from app.models.organizacao import Organizacao
from app.models.projeto import Projeto, ProjetoUsuario, RotuloProjeto
from app.models.setor import Setor
from app.models.usuario import Usuario
from app.services.identidade import (
    ErroAuth,
    criar_convite,
    email_acesso,
)

ROTULOS = (
    ("CLIMA", "Clima organizacional", 1),
    ("DESEMPENHO", "Desempenho", 2),
    ("CARGOS_SALARIOS", "Cargos e salários", 3),
    ("PERSONALIZADA", "Personalizada", 4),
)
VINCULOS = {"EDITAL", "DOCUMENTO"}
ESTADOS = {"ABERTO", "EM_ANDAMENTO", "ENCERRADO", "ARQUIVADO"}
IA_SUSPENSA = "DESATIVADA"


def garantir_rotulos(db: Session) -> None:
    existentes = {
        item.codigo
        for item in db.scalars(select(RotuloProjeto)).all()
    }
    for codigo, nome, ordem in ROTULOS:
        if codigo in existentes:
            continue
        db.add(
            RotuloProjeto(
                id=novo_id(),
                codigo=codigo,
                nome=nome,
                ordem=ordem,
            )
        )
    db.commit()


def listar_rotulos(db: Session) -> list[RotuloProjeto]:
    garantir_rotulos(db)
    return list(
        db.scalars(select(RotuloProjeto).order_by(RotuloProjeto.ordem)).all()
    )


def _participa(db: Session, usuario: Usuario, projeto_id: str) -> bool:
    """Só quem tem vínculo no projeto vivo. Soft delete corta o acesso."""
    projeto = db.get(Projeto, projeto_id)
    if projeto is None or projeto.deleted_at is not None:
        return False
    if usuario.papel == "CONSULTOR" and projeto.consultor_id == usuario.id:
        return True
    vinculo = db.scalar(
        select(ProjetoUsuario.id).where(
            ProjetoUsuario.projeto_id == projeto_id,
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    return vinculo is not None


def listar_projetos(db: Session, usuario: Usuario) -> list["ProjetoSaidaMontada"]:
    if usuario.papel == "TI":
        raise ErroAuth(403, "Sem acesso a projetos.")
    garantir_rotulos(db)
    if usuario.papel == "CONSULTOR":
        projetos = db.scalars(
            select(Projeto).where(
                Projeto.consultor_id == usuario.id,
                Projeto.deleted_at.is_(None),
            )
        ).all()
    else:
        ids = db.scalars(
            select(ProjetoUsuario.projeto_id).where(
                ProjetoUsuario.usuario_id == usuario.id
            )
        ).all()
        if not ids:
            return []
        projetos = db.scalars(
            select(Projeto).where(
                Projeto.id.in_(ids),
                Projeto.deleted_at.is_(None),
            )
        ).all()
    return [_montar(db, item) for item in projetos]


def obter_projeto(
    db: Session, usuario: Usuario, projeto_id: str
) -> "ProjetoSaidaMontada":
    if usuario.papel == "TI" or not _participa(db, usuario, projeto_id):
        raise ErroAuth(404, "Projeto não encontrado.")
    projeto = db.get(Projeto, projeto_id)
    if projeto is None or projeto.deleted_at is not None:
        raise ErroAuth(404, "Projeto não encontrado.")
    return _montar(db, projeto)


def criar_projeto(
    db: Session,
    consultor: Usuario,
    rotulo_id: str,
    cnpj: str,
    email_orgao: str,
    vinculo_tipo: str,
    vinculo_titulo: str,
) -> "ProjetoSaidaMontada":
    if consultor.papel != "CONSULTOR":
        raise ErroAuth(403, "Só a consultora cria projeto.")
    if vinculo_tipo not in VINCULOS:
        raise ErroAuth(422, "Vínculo deve ser EDITAL ou DOCUMENTO.")
    garantir_rotulos(db)
    rotulo = db.get(RotuloProjeto, rotulo_id)
    if rotulo is None:
        raise ErroAuth(422, "Rótulo inválido.")

    try:
        dados = buscar(cnpj)
    except CnpjInvalido as exc:
        raise ErroAuth(422, str(exc)) from None
    except CnpjNaoEncontrado as exc:
        raise ErroAuth(404, str(exc)) from None
    except CnpjIndisponivel as exc:
        raise ErroAuth(503, str(exc)) from None

    endereco = email_acesso(email_orgao)
    orgao = _org_por_cnpj(db, dados)
    # B7: mesmo CNPJ ativo na mesma consultora = retry/duplicata.
    duplicado = db.scalar(
        select(Projeto.id)
        .join(Organizacao, Organizacao.id == Projeto.organizacao_id)
        .where(
            Projeto.consultor_id == consultor.id,
            Projeto.deleted_at.is_(None),
            Organizacao.cnpj == dados.cnpj,
            Organizacao.deleted_at.is_(None),
        )
    )
    if duplicado is not None:
        raise ErroAuth(409, "Já existe projeto ativo com este CNPJ.")
    projeto = Projeto(
        organizacao_id=orgao.id,
        consultor_id=consultor.id,
        rotulo_id=rotulo.id,
        estado="ABERTO",
        vinculo_tipo=vinculo_tipo,
        vinculo_titulo=vinculo_titulo.strip(),
    )
    db.add(projeto)
    db.flush()
    db.add(
        ProjetoUsuario(
            id=novo_id(),
            projeto_id=projeto.id,
            usuario_id=consultor.id,
            papel="CONSULTOR",
        )
    )
    db.add(
        ConfiguracaoProjeto(
            projeto_id=projeto.id,
            pesquisas_habilitadas=False,
            ia_modo=IA_SUSPENSA,
        )
    )
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=consultor.id,
            acao="PROJETO_CRIADO",
            criado_em=projeto.criado_em,
        )
    )
    db.commit()
    link_orgao: str | None = None
    try:
        convite_saida = criar_convite(
            db,
            consultor,
            dados.razao_social[:160],
            endereco,
            "ORGAO",
            projeto_id=projeto.id,
        )
        link_orgao = convite_saida.get("link_primeiro_acesso")
    except ErroAuth as exc:
        # B8: o projeto já nasceu. Não apaga; grava estado legível.
        if exc.status == 409:
            _tratar_orgao_ja_existente(db, consultor, projeto, endereco)
        elif exc.status == 429:
            _registrar_convite_pendente(
                db,
                consultor,
                projeto,
                dados.razao_social[:160],
                endereco,
                motivo="limite_de_convites",
                acao="CONVITE_AGUARDANDO",
            )
        else:
            raise
    montado = _montar(db, projeto)
    montado.link_primeiro_acesso = link_orgao
    return montado


def _projeto_da_consultora(db: Session, usuario: Usuario, projeto_id: str) -> Projeto:
    if usuario.papel != "CONSULTOR":
        raise ErroAuth(404, "Projeto não encontrado.")
    projeto = db.get(Projeto, projeto_id)
    if (
        projeto is None
        or projeto.deleted_at is not None
        or projeto.consultor_id != usuario.id
    ):
        raise ErroAuth(404, "Projeto não encontrado.")
    return projeto


def atualizar_projeto(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    estado: str | None,
    vinculo_titulo: str | None,
) -> "ProjetoSaidaMontada":
    projeto = _projeto_da_consultora(db, consultor, projeto_id)
    if estado is None and vinculo_titulo is None:
        raise ErroAuth(422, "Nada para atualizar.")
    if estado is not None:
        if estado not in ESTADOS:
            raise ErroAuth(422, "Estado inválido.")
        projeto.estado = estado
    if vinculo_titulo is not None:
        projeto.vinculo_titulo = vinculo_titulo.strip()
    projeto.atualizado_em = agora()
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=consultor.id,
            acao="PROJETO_ATUALIZADO",
            criado_em=agora(),
        )
    )
    db.commit()
    return _montar(db, projeto)


def reenviar_convite(
    db: Session, consultor: Usuario, projeto_id: str
) -> dict[str, str | None]:
    """Novo token se o órgão ainda não aceitou. O token antigo deixa de valer."""
    projeto = _projeto_da_consultora(db, consultor, projeto_id)
    convite = db.scalar(
        select(Convite)
        .where(
            Convite.projeto_id == projeto.id,
            Convite.papel == "ORGAO",
        )
        .order_by(Convite.criado_em.desc())
    )
    if convite is None:
        raise ErroAuth(404, "Convite não encontrado.")
    if convite.status == "ACEITO":
        raise ErroAuth(409, "O órgão já aceitou o convite.")
    convite.status = "CANCELADO"
    convite.atualizado_em = agora()
    db.commit()
    saida = criar_convite(
        db,
        consultor,
        convite.nome,
        convite.email,
        convite.papel,
        projeto_id=projeto.id,
    )
    return {
        "email": convite.email,
        "link_primeiro_acesso": saida.get("link_primeiro_acesso"),
    }


def listar_equipe(db: Session, consultor: Usuario, projeto_id: str) -> list[dict]:
    """Órgão e funcionários do trabalho. Sem token e sem senha."""
    projeto = _projeto_da_consultora(db, consultor, projeto_id)
    itens: list[dict] = []
    vistos: set[str] = set()
    vinculos = db.scalars(
        select(ProjetoUsuario).where(ProjetoUsuario.projeto_id == projeto.id)
    ).all()
    for vinculo in vinculos:
        if vinculo.papel not in {"ORGAO", "FUNCIONARIO"}:
            continue
        pessoa = db.get(Usuario, vinculo.usuario_id)
        if pessoa is None or pessoa.deleted_at is not None:
            continue
        vistos.add(pessoa.email)
        itens.append(
            {
                "nome": pessoa.nome,
                "email": pessoa.email,
                "papel": vinculo.papel,
                "situacao": "ATIVO" if pessoa.ativo else "INATIVO",
            }
        )
    convites = db.scalars(
        select(Convite)
        .where(
            Convite.projeto_id == projeto.id,
            Convite.papel.in_(("ORGAO", "FUNCIONARIO")),
            Convite.status == "PENDENTE",
        )
        .order_by(Convite.criado_em.desc())
    ).all()
    for convite in convites:
        if convite.email in vistos:
            continue
        vistos.add(convite.email)
        itens.append(
            {
                "nome": convite.nome,
                "email": convite.email,
                "papel": convite.papel,
                "situacao": "PENDENTE",
            }
        )
    return itens


def listar_setores(db: Session, usuario: Usuario, projeto_id: str) -> list[Setor]:
    if not _participa(db, usuario, projeto_id):
        raise ErroAuth(404, "Projeto não encontrado.")
    return list(
        db.scalars(
            select(Setor).where(
                Setor.projeto_id == projeto_id,
                Setor.deleted_at.is_(None),
            )
        ).all()
    )


def criar_setor(
    db: Session, consultor: Usuario, projeto_id: str, nome: str
) -> Setor:
    projeto = _projeto_da_consultora(db, consultor, projeto_id)
    setor = Setor(projeto_id=projeto.id, nome=nome.strip())
    db.add(setor)
    db.flush()
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=consultor.id,
            acao="SETOR_CRIADO",
            criado_em=agora(),
        )
    )
    db.commit()
    return setor


def remover_setor(
    db: Session, consultor: Usuario, projeto_id: str, setor_id: str
) -> None:
    _projeto_da_consultora(db, consultor, projeto_id)
    setor = db.get(Setor, setor_id)
    if setor is None or setor.projeto_id != projeto_id or setor.deleted_at is not None:
        raise ErroAuth(404, "Setor não encontrado.")
    setor.deleted_at = agora()
    setor.atualizado_em = agora()
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=consultor.id,
            acao="SETOR_REMOVIDO",
            criado_em=agora(),
        )
    )
    db.commit()


def obter_configuracao(
    db: Session, usuario: Usuario, projeto_id: str
) -> ConfiguracaoProjeto:
    if not _participa(db, usuario, projeto_id):
        raise ErroAuth(404, "Projeto não encontrado.")
    config = db.scalar(
        select(ConfiguracaoProjeto).where(
            ConfiguracaoProjeto.projeto_id == projeto_id
        )
    )
    if config is None:
        raise ErroAuth(404, "Configuração não encontrada.")
    return config


def atualizar_configuracao(
    db: Session,
    consultor: Usuario,
    projeto_id: str,
    pesquisas_habilitadas: bool,
) -> ConfiguracaoProjeto:
    _projeto_da_consultora(db, consultor, projeto_id)
    config = db.scalar(
        select(ConfiguracaoProjeto).where(
            ConfiguracaoProjeto.projeto_id == projeto_id
        )
    )
    if config is None:
        raise ErroAuth(404, "Configuração não encontrada.")
    config.pesquisas_habilitadas = pesquisas_habilitadas
    config.ia_modo = IA_SUSPENSA
    config.atualizado_em = agora()
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=consultor.id,
            acao="CONFIG_ATUALIZADA",
            criado_em=agora(),
        )
    )
    db.commit()
    return config


def vincular_aceite(db: Session, convite: Convite, usuario: Usuario) -> None:
    if not convite.projeto_id:
        return
    ja = db.scalar(
        select(ProjetoUsuario.id).where(
            ProjetoUsuario.projeto_id == convite.projeto_id,
            ProjetoUsuario.usuario_id == usuario.id,
        )
    )
    if ja is not None:
        return
    db.add(
        ProjetoUsuario(
            id=novo_id(),
            projeto_id=convite.projeto_id,
            usuario_id=usuario.id,
            papel=convite.papel,
        )
    )


def _org_por_cnpj(db: Session, dados: DadosCnpj) -> Organizacao:
    orgao = db.scalar(
        select(Organizacao).where(
            Organizacao.cnpj == dados.cnpj,
            Organizacao.deleted_at.is_(None),
        )
    )
    if orgao is None:
        orgao = Organizacao(
            cnpj=dados.cnpj,
            razao_social=dados.razao_social,
            nome_fantasia=dados.nome_fantasia,
            municipio=dados.municipio,
            uf=dados.uf,
        )
        db.add(orgao)
        db.flush()
        return orgao
    orgao.razao_social = dados.razao_social
    orgao.nome_fantasia = dados.nome_fantasia
    orgao.municipio = dados.municipio
    orgao.uf = dados.uf
    return orgao


class ProjetoSaidaMontada:
    def __init__(
        self,
        id: str,
        rotulo_id: str,
        rotulo: str,
        estado: str,
        cnpj: str,
        razao_social: str,
        nome_fantasia: str | None,
        email_orgao: str,
        vinculo_tipo: str,
        vinculo_titulo: str,
        convite_entrega: str,
        onboarding_estado: str,
        convite_motivo: str | None,
        link_primeiro_acesso: str | None = None,
    ) -> None:
        self.id = id
        self.rotulo_id = rotulo_id
        self.rotulo = rotulo
        self.estado = estado
        self.cnpj = cnpj
        self.razao_social = razao_social
        self.nome_fantasia = nome_fantasia
        self.email_orgao = email_orgao
        self.vinculo_tipo = vinculo_tipo
        self.vinculo_titulo = vinculo_titulo
        self.convite_entrega = convite_entrega
        self.onboarding_estado = onboarding_estado
        self.convite_motivo = convite_motivo
        self.link_primeiro_acesso = link_primeiro_acesso


def _tratar_orgao_ja_existente(
    db: Session,
    consultor: Usuario,
    projeto: Projeto,
    endereco: str,
) -> None:
    existente = db.scalar(
        select(Usuario).where(
            Usuario.email == endereco,
            Usuario.deleted_at.is_(None),
        )
    )
    if (
        existente is not None
        and existente.papel == "ORGAO"
        and existente.ativo
    ):
        ja = db.scalar(
            select(ProjetoUsuario.id).where(
                ProjetoUsuario.projeto_id == projeto.id,
                ProjetoUsuario.usuario_id == existente.id,
            )
        )
        if ja is None:
            db.add(
                ProjetoUsuario(
                    id=novo_id(),
                    projeto_id=projeto.id,
                    usuario_id=existente.id,
                    papel="ORGAO",
                )
            )
        db.add(
            LogAuditoria(
                id=novo_id(),
                usuario_id=consultor.id,
                acao="ORGAO_VINCULADO",
                criado_em=agora(),
            )
        )
        db.commit()
        return
    motivo = _motivo_nao_enviado(existente)
    _registrar_convite_pendente(
        db,
        consultor,
        projeto,
        (existente.nome if existente else endereco.split("@")[0])[:160],
        endereco,
        motivo=motivo,
        acao="CONVITE_NAO_ENVIADO",
        status="CANCELADO",
    )


def _motivo_nao_enviado(existente: Usuario | None) -> str:
    if existente is None:
        return "email_indisponivel"
    if not existente.ativo:
        return "conta_inativa"
    if existente.papel == "FUNCIONARIO":
        return "email_ja_e_funcionario"
    if existente.papel == "CONSULTOR":
        return "email_ja_e_consultor"
    if existente.papel == "TI":
        return "email_ja_e_ti"
    if existente.papel == "ORGAO":
        return "conta_inativa"
    return "email_ja_tem_acesso"


def _registrar_convite_pendente(
    db: Session,
    consultor: Usuario,
    projeto: Projeto,
    nome: str,
    endereco: str,
    *,
    motivo: str,
    acao: str,
    status: str = "PENDENTE",
) -> None:
    """Guarda o e-mail pretendido sem token válido de primeiro acesso.

    Assim a tela mostra onboarding e motivo (B8/B9) mesmo quando o
    criar_convite não chegou a gravar a linha.
    """
    entrega = "LIMITE_CONVITES" if motivo == "limite_de_convites" else "NAO_ENVIADO"
    token = novo_token_opaco()
    db.add(
        Convite(
            email=endereco,
            nome=nome.strip()[:160],
            papel="ORGAO",
            token_hash=hash_token(token),
            status=status,
            entrega=entrega,
            expira_em=agora() + timedelta(hours=48),
            convidado_por_id=consultor.id,
            projeto_id=projeto.id,
        )
    )
    db.add(
        LogAuditoria(
            id=novo_id(),
            usuario_id=consultor.id,
            acao=acao,
            criado_em=agora(),
        )
    )
    db.commit()


def _montar(db: Session, projeto: Projeto) -> "ProjetoSaidaMontada":
    orgao = db.get(Organizacao, projeto.organizacao_id)
    rotulo = db.get(RotuloProjeto, projeto.rotulo_id)
    convite = db.scalar(
        select(Convite)
        .where(
            Convite.projeto_id == projeto.id,
            Convite.papel == "ORGAO",
        )
        .order_by(Convite.criado_em.desc())
    )
    email_orgao = convite.email if convite else ""
    entrega = convite.entrega if convite else "NAO_ENVIADO"
    orgao_vinculado = False
    vinculo = db.scalar(
        select(ProjetoUsuario).where(
            ProjetoUsuario.projeto_id == projeto.id,
            ProjetoUsuario.papel == "ORGAO",
        )
    )
    if vinculo is not None:
        pessoa_orgao = db.get(Usuario, vinculo.usuario_id)
        if pessoa_orgao is not None and pessoa_orgao.deleted_at is None:
            orgao_vinculado = True
            if not email_orgao:
                email_orgao = pessoa_orgao.email
            if convite is None or convite.status not in {"PENDENTE", "CANCELADO"}:
                entrega = "ENVIADO"

    onboarding, motivo = _estado_onboarding(
        db, convite, orgao_vinculado, email_orgao
    )
    return ProjetoSaidaMontada(
        id=projeto.id,
        rotulo_id=projeto.rotulo_id,
        rotulo=rotulo.nome if rotulo else "",
        estado=projeto.estado,
        cnpj=orgao.cnpj if orgao else "",
        razao_social=orgao.razao_social if orgao else "",
        nome_fantasia=orgao.nome_fantasia if orgao else None,
        email_orgao=email_orgao,
        vinculo_tipo=projeto.vinculo_tipo,
        vinculo_titulo=projeto.vinculo_titulo,
        convite_entrega=entrega,
        onboarding_estado=onboarding,
        convite_motivo=motivo,
    )


def _estado_onboarding(
    db: Session,
    convite: Convite | None,
    orgao_vinculado: bool,
    email_orgao: str,
) -> tuple[str, str | None]:
    if orgao_vinculado:
        return "orgao_aceitou", None
    if convite is None:
        return "convite_pendente", "sem_convite"
    expira = convite.expira_em
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=UTC)
    if convite.status == "PENDENTE" and expira <= agora():
        return "convite_expirado", None
    if convite.entrega == "LIMITE_CONVITES":
        return "convite_pendente", "limite_de_convites"
    if convite.entrega == "FALHA":
        return "convite_pendente", "falha_de_envio"
    if convite.status == "CANCELADO" or convite.entrega == "NAO_ENVIADO":
        existente = db.scalar(
            select(Usuario).where(
                Usuario.email == email_orgao,
                Usuario.deleted_at.is_(None),
            )
        )
        if existente is not None:
            return "convite_pendente", _motivo_nao_enviado(existente)
        return "convite_pendente", "aguardando_envio"
    if convite.status == "PENDENTE" and convite.entrega == "ENVIADO":
        return "convite_enviado", None
    return "convite_pendente", None

