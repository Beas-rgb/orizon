"""Criação e listagem de cenários do laboratório."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tokens import novo_id
from app.models.base import agora
from app.models.configuracao import ConfiguracaoProjeto
from app.models.controle_acesso import ControleAcesso
from app.models.lab import CenarioLab
from app.models.organizacao import Organizacao
from app.models.projeto import Projeto, ProjetoUsuario, RotuloProjeto
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth
from app.services.importacao import LinhaImportacao, confirmar_importacao
from app.services.lab.geradores import (
    PERFIS,
    TAMANHOS,
    TIPOS_CENARIO,
    cnpj_sintetico,
    montar_linhas,
    perguntas_clima,
)
from app.services.pesquisa.crud import adicionar_pergunta, criar_pesquisa, publicar
from app.services.projeto import IA_SUSPENSA, garantir_rotulos

LOTE = 500
LIMITE_CRIACOES_HORA = 6


def _ciente(valor):
    from datetime import UTC

    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor


def listar_cenarios(db: Session, dono: Usuario) -> list[CenarioLab]:
    return list(
        db.scalars(
            select(CenarioLab)
            .where(CenarioLab.dono_id == dono.id)
            .order_by(CenarioLab.criado_em.desc())
        ).all()
    )


def obter_cenario(db: Session, dono: Usuario, cenario_id: str) -> CenarioLab:
    linha = db.get(CenarioLab, cenario_id)
    if linha is None or linha.dono_id != dono.id:
        raise ErroAuth(404, "Não encontrado.")
    return linha


def _banco_acima_do_limite(db: Session) -> bool:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    try:
        bytes_ = db.scalar(text("SELECT pg_database_size(current_database())"))
    except Exception:
        return False
    if bytes_ is None:
        return False
    return int(bytes_) > settings.lab_limite_banco_mb * 1024 * 1024


def _rate_criar(db: Session, dono_id: str) -> None:
    chave = f"lab:criar:{dono_id}"
    agora_ = agora()
    linha = db.get(ControleAcesso, chave)
    if linha is None:
        linha = ControleAcesso(
            chave=chave,
            tentativas=0,
            bloqueado_ate=None,
            atualizado_em=agora_,
        )
        db.add(linha)
        db.flush()
    atualizado = _ciente(linha.atualizado_em) or agora_
    if agora_ - atualizado > timedelta(hours=1):
        linha.tentativas = 0
        linha.bloqueado_ate = None
    bloqueado = _ciente(linha.bloqueado_ate)
    if bloqueado and bloqueado > agora_:
        raise ErroAuth(429, "Muitas criações. Aguarde e tente de novo.")
    linha.tentativas += 1
    linha.atualizado_em = agora_
    if linha.tentativas > LIMITE_CRIACOES_HORA:
        linha.bloqueado_ate = agora_ + timedelta(hours=1)
        db.flush()
        raise ErroAuth(429, "Muitas criações. Aguarde e tente de novo.")
    db.flush()


def solicitar_cenario(
    db: Session,
    dono: Usuario,
    nome: str,
    tipo: str,
    tamanho: int,
    perfil: str,
    seed: int | None,
    com_senha: bool,
) -> CenarioLab:
    if tipo not in TIPOS_CENARIO:
        raise ErroAuth(422, "Tipo de cenário inválido.")
    if tamanho not in TAMANHOS:
        raise ErroAuth(422, "Tamanho inválido.")
    if tamanho > settings.lab_max_participantes:
        raise ErroAuth(422, "Tamanho acima do limite do ambiente.")
    if perfil not in PERFIS:
        raise ErroAuth(422, "Perfil inválido.")
    if com_senha and not settings.lab_tokens_permitidos:
        raise ErroAuth(422, "Senha sintética só no staging.")
    andamento = db.scalar(
        select(CenarioLab.id).where(
            CenarioLab.dono_id == dono.id,
            CenarioLab.status.in_(("CRIANDO", "EXCLUINDO")),
        )
    )
    if andamento is not None:
        raise ErroAuth(409, "Já existe um cenário em andamento.")
    if _banco_acima_do_limite(db):
        raise ErroAuth(409, "Banco próximo do limite. Apague um cenário.")
    _rate_criar(db, dono.id)
    agora_ = agora()
    cenario = CenarioLab(
        id=novo_id(),
        dono_id=dono.id,
        nome=nome.strip()[:160],
        tipo=tipo,
        tamanho=tamanho,
        seed=seed if seed is not None else int(agora_.timestamp()) % 1_000_000,
        perfil=perfil,
        status="CRIANDO",
        projeto_id=None,
        progresso=0,
        erro=None,
        criado_em=agora_,
        atualizado_em=agora_,
    )
    db.add(cenario)
    db.commit()
    db.refresh(cenario)
    return cenario


def _marcar(db: Session, cenario_id: str, progresso: int, **extra) -> None:
    valores = {"progresso": progresso, "atualizado_em": agora(), **extra}
    db.execute(
        update(CenarioLab).where(CenarioLab.id == cenario_id).values(**valores)
    )
    db.commit()


def _criar_projeto_lab(
    db: Session,
    dono: Usuario,
    cenario: CenarioLab,
) -> Projeto:
    garantir_rotulos(db)
    codigo = "CLIMA" if cenario.tipo == "CLIMA" else "DESEMPENHO"
    rotulo = db.scalar(
        select(RotuloProjeto).where(RotuloProjeto.codigo == codigo)
    )
    if rotulo is None:
        rotulo = db.scalar(select(RotuloProjeto).limit(1))
    if rotulo is None:
        raise ErroAuth(500, "Rótulo ausente.")
    cnpj = cnpj_sintetico(cenario.seed, cenario.id)
    agora_ = agora()
    org = Organizacao(
        id=novo_id(),
        cnpj=cnpj,
        razao_social=f"LAB {cenario.nome}"[:200],
        nome_fantasia=None,
        municipio="Lab",
        uf="DF",
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )
    db.add(org)
    db.flush()
    projeto = Projeto(
        id=novo_id(),
        organizacao_id=org.id,
        consultor_id=dono.id,
        rotulo_id=rotulo.id,
        estado="ABERTO",
        vinculo_tipo="EDITAL",
        vinculo_titulo=f"Lab {cenario.id[:8]}",
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )
    db.add(projeto)
    db.flush()
    db.add(
        ProjetoUsuario(
            id=novo_id(),
            projeto_id=projeto.id,
            usuario_id=dono.id,
            papel="CONSULTOR",
        )
    )
    db.add(
        ConfiguracaoProjeto(
            id=novo_id(),
            projeto_id=projeto.id,
            pesquisas_habilitadas=True,
            ia_modo=IA_SUSPENSA,
            criado_em=agora_,
            atualizado_em=agora_,
        )
    )
    db.commit()
    db.refresh(projeto)
    return projeto


def _importar_em_lotes(
    db: Session,
    dono: Usuario,
    projeto_id: str,
    linhas: list[LinhaImportacao],
    cenario_id: str,
) -> None:
    total = len(linhas)
    for inicio in range(0, total, LOTE):
        fatia = linhas[inicio : inicio + LOTE]
        confirmar_importacao(db, dono, projeto_id, fatia)
        pct = min(80, int(20 + 60 * (inicio + len(fatia)) / total))
        _marcar(db, cenario_id, pct)


def _marcar_sinteticos(
    db: Session,
    cenario_id: str,
    senha_hash: str | None,
) -> None:
    dominio = f".{cenario_id[:8]}@sintetico.invalid"
    pessoas = list(
        db.scalars(
            select(Usuario).where(
                Usuario.email.like(f"%{dominio}"),
                Usuario.deleted_at.is_(None),
            )
        ).all()
    )
    for pessoa in pessoas:
        pessoa.tipo_conta = "SINTETICO"
        pessoa.ativo = True
        if senha_hash is not None:
            pessoa.senha_hash = senha_hash
        pessoa.atualizado_em = agora()
    db.commit()


def _montar_pesquisa_clima(
    db: Session,
    dono: Usuario,
    projeto_id: str,
) -> None:
    pesquisa = criar_pesquisa(
        db,
        dono,
        projeto_id,
        "Clima lab",
        "CLIMA",
        "Pesquisa sintética",
    )
    for item in perguntas_clima():
        adicionar_pergunta(
            db,
            dono,
            pesquisa.id,
            str(item["texto"]),
            str(item["tipo"]),
            True,
            list(item["opcoes"]),
        )
    publicar(db, dono, pesquisa.id, tarefas=None)


def executar_criacao(cenario_id: str, com_senha: bool) -> None:
    """Roda fora do request, com sessão própria."""
    from app.core.database import SessionLocal, get_engine
    from app.core.security import hash_senha

    get_engine()
    if SessionLocal is None:
        return
    with SessionLocal() as db:
        cenario = db.get(CenarioLab, cenario_id)
        if cenario is None or cenario.status != "CRIANDO":
            return
        dono = db.get(Usuario, cenario.dono_id)
        if dono is None:
            _marcar(
                db,
                cenario_id,
                0,
                status="ERRO",
                erro="Dono ausente.",
            )
            return
        try:
            _marcar(db, cenario_id, 5)
            projeto = _criar_projeto_lab(db, dono, cenario)
            cenario = db.get(CenarioLab, cenario_id)
            if cenario is None:
                return
            cenario.projeto_id = projeto.id
            db.commit()
            _marcar(db, cenario_id, 15)
            linhas = montar_linhas(cenario.tamanho, cenario.seed, cenario.id)
            _importar_em_lotes(db, dono, projeto.id, linhas, cenario_id)
            senha_hash = None
            if com_senha:
                # Um único hash para todos — evita 5.000 Argon2.
                senha_hash = hash_senha("Senha-lab-teste1!")
            _marcar_sinteticos(db, cenario_id, senha_hash)
            _marcar(db, cenario_id, 85)
            if cenario.tipo == "CLIMA":
                _montar_pesquisa_clima(db, dono, projeto.id)
            else:
                _montar_pesquisa_clima(db, dono, projeto.id)
            _marcar(db, cenario_id, 100, status="PRONTO", erro=None)
        except ErroAuth as exc:
            _marcar(
                db,
                cenario_id,
                0,
                status="ERRO",
                erro=str(exc.detalhe)[:500],
            )
        except Exception as exc:
            _marcar(
                db,
                cenario_id,
                0,
                status="ERRO",
                erro=type(exc).__name__[:500],
            )


def cenario_saida(linha: CenarioLab) -> dict[str, object]:
    return {
        "id": linha.id,
        "nome": linha.nome,
        "tipo": linha.tipo,
        "tamanho": linha.tamanho,
        "seed": linha.seed,
        "perfil": linha.perfil,
        "status": linha.status,
        "projeto_id": linha.projeto_id,
        "progresso": linha.progresso,
        "erro": linha.erro,
    }
