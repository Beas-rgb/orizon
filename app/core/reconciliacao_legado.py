"""Reconciliação manual de um banco legado sem alembic_version.

Uso só em cópia isolada. O boot não importa este módulo.

O schema do banco é comparado com os modelos, que o teste de drift prova
iguais ao head das migrations no PostgreSQL. Qualquer diferença bloqueia o
registro do head. Nada é renomeado, copiado ou apagado: tabela extra fica
como está e aparece no relatório. A única escrita possível é criar
`alembic_version` com o head, numa transação, depois de uma segunda
comparação sem divergência.

`RECONCILIAR_URL=... python -m app.core.reconciliacao_legado [COPIA_ISOLADA]`
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection

CONFIRMACAO = "COPIA_ISOLADA"

# Origem legada que não vira destino sem regra aprovada. Token em claro não
# é hash: links antigos precisam ser reemitidos.
SEM_REGRA = (
    ("usuarios", "nome_completo", "nome"),
    ("convites", "token", "token_hash"),
    ("tokens_resposta", "token", "token_hash"),
    ("projetos", "criado_por", "consultor_id"),
    ("organizacoes", "nome", "razao_social"),
    ("documentos", "enviado_por", "consultor_id"),
    ("documentos", "projeto_origem_id", "projeto_id"),
    ("configuracoes_projeto", "ia_ativa", "ia_modo"),
)


class ReconciliacaoRecusada(RuntimeError):
    pass


@dataclass
class Relatorio:
    tabelas_extras: list[str] = field(default_factory=list)
    divergencias: list[str] = field(default_factory=list)
    sem_regra: list[str] = field(default_factory=list)

    @property
    def equivalente(self) -> bool:
        return not (self.tabelas_extras or self.divergencias or self.sem_regra)


def _descrever(diferenca) -> tuple[str, str]:
    if isinstance(diferenca, list):
        item = diferenca[0]
        return item[0], f"{item[2]}.{item[3]}"
    operacao = diferenca[0]
    objeto = diferenca[1]
    if operacao in {"add_table", "remove_table"}:
        return operacao, objeto.name
    if operacao in {"add_column", "remove_column"}:
        return operacao, f"{diferenca[2]}.{diferenca[3].name}"
    if operacao in {"add_index", "remove_index"}:
        return operacao, f"{objeto.table.name}.{objeto.name}"
    tabela = getattr(getattr(objeto, "table", None), "name", "?")
    return operacao, f"{tabela}.{getattr(objeto, 'name', None) or '?'}"


def comparar(conexao: Connection) -> Relatorio:
    import app.models  # noqa: F401
    from app.models.base import Base

    postgres = conexao.dialect.name == "postgresql"
    contexto = MigrationContext.configure(
        conexao,
        opts={
            "compare_type": postgres,
            "compare_server_default": postgres,
            "include_name": lambda nome, tipo, _pai: not (
                tipo == "table" and nome == "alembic_version"
            ),
        },
    )
    relatorio = Relatorio()
    for diferenca in compare_metadata(contexto, Base.metadata):
        operacao, alvo = _descrever(diferenca)
        if operacao == "remove_table":
            relatorio.tabelas_extras.append(alvo)
        else:
            relatorio.divergencias.append(f"{operacao} {alvo}")

    insp = inspect(conexao)
    tabelas = set(insp.get_table_names())
    for tabela, origem, destino in SEM_REGRA:
        if tabela not in tabelas:
            continue
        colunas = {coluna["name"] for coluna in insp.get_columns(tabela)}
        if origem in colunas and destino not in colunas:
            relatorio.sem_regra.append(f"{tabela}.{origem} -> {destino}")
    relatorio.tabelas_extras.sort()
    relatorio.divergencias.sort()
    return relatorio


def _normalizar(url: str) -> str:
    return url.strip().rstrip("/")


def validar_destino(url: str, confirmacao: str) -> None:
    """Recusa antes de abrir conexão."""
    from app.core.config import settings

    if settings.app_env == "production":
        raise ReconciliacaoRecusada("APP_ENV=production")
    if confirmacao != CONFIRMACAO:
        raise ReconciliacaoRecusada(f"confirmação diferente de {CONFIRMACAO}")
    destino = _normalizar(url)
    if not destino:
        raise ReconciliacaoRecusada("URL de destino vazia")
    proibidas = {
        _normalizar(valor)
        for valor in (
            settings.database_url,
            settings.database_url_direct,
            os.environ.get("DATABASE_URL", ""),
        )
        if valor.strip()
    }
    if destino in proibidas:
        raise ReconciliacaoRecusada("destino igual ao banco da aplicação")


def _estado(conexao: Connection) -> None:
    tabelas = set(inspect(conexao).get_table_names())
    if not tabelas:
        raise ReconciliacaoRecusada("banco vazio: use o upgrade normal")
    if "alembic_version" in tabelas:
        raise ReconciliacaoRecusada("alembic_version já existe")


def inspecionar(url: str, confirmacao: str) -> Relatorio:
    validar_destino(url, confirmacao)
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            _estado(conexao)
            return comparar(conexao)
    finally:
        engine.dispose()


def registrar_head(url: str, confirmacao: str, head: str) -> Relatorio:
    """Cria alembic_version com o head só se nada divergir."""
    validar_destino(url, confirmacao)
    engine = create_engine(url)
    try:
        with engine.begin() as conexao:
            _estado(conexao)
            relatorio = comparar(conexao)
            if not relatorio.equivalente:
                raise ReconciliacaoRecusada("schema diferente do head")
            conexao.execute(
                text(
                    "CREATE TABLE alembic_version ("
                    "version_num VARCHAR(32) NOT NULL, "
                    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                )
            )
            conexao.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
                {"v": head},
            )
            if not comparar(conexao).equivalente:
                raise ReconciliacaoRecusada("schema mudou durante o registro")
        return relatorio
    finally:
        engine.dispose()


def main(argv: list[str]) -> int:
    url = os.environ.get("RECONCILIAR_URL", "")
    confirmacao = argv[1] if len(argv) > 1 else ""
    try:
        relatorio = inspecionar(url, confirmacao)
    except ReconciliacaoRecusada as exc:
        print("recusado:", exc)
        return 2
    print("equivalente:", relatorio.equivalente)
    for rotulo, itens in (
        ("tabela extra preservada", relatorio.tabelas_extras),
        ("divergência", relatorio.divergencias),
        ("sem regra de cópia", relatorio.sem_regra),
    ):
        for item in itens:
            print(f"{rotulo}: {item}")
    return 0 if relatorio.equivalente else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
