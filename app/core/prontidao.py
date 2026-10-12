"""Diz se a API pode atender com o schema e o armazenamento encontrados.

Só leitura. Os motivos são códigos fixos: não levam nome de tabela, host
nem texto do driver.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

BANCO_INDISPONIVEL = "banco_indisponivel"
SCHEMA_SEM_VERSAO = "schema_sem_versao"
REVISAO_DIVERGENTE = "revisao_divergente"
TABELAS_AUSENTES = "tabelas_ausentes"
ARMAZENAMENTO_AUSENTE = "armazenamento_ausente"


def motivos_do_ambiente() -> list[str]:
    from app.core.config import settings
    from app.integrations.arquivos import r2_configurado

    if settings.app_env == "production" and not r2_configurado():
        return [ARMAZENAMENTO_AUSENTE]
    return []


def revisao_esperada() -> str:
    from app.core.migracao import _revisao_esperada, mapa_revisoes

    try:
        return _revisao_esperada()
    except SystemExit:
        return mapa_revisoes()[0]


def motivos_do_schema(conexao: Connection, esperada: str) -> list[str]:
    import app.models  # noqa: F401
    from app.models.base import Base

    schema = "public" if conexao.dialect.name == "postgresql" else None
    tabelas = set(inspect(conexao).get_table_names(schema=schema))
    motivos: list[str] = []
    if "alembic_version" not in tabelas:
        motivos.append(SCHEMA_SEM_VERSAO)
    else:
        versoes = (
            conexao.execute(text("select version_num from alembic_version"))
            .scalars()
            .all()
        )
        if versoes != [esperada]:
            motivos.append(REVISAO_DIVERGENTE)
    if set(Base.metadata.tables) - tabelas:
        motivos.append(TABELAS_AUSENTES)
    return motivos
