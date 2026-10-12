"""Limpa o banco mantendo só contas TI (dev). Não imprime URL nem senha.

Só roda fora de produção, num host local ou listado em HORIZON_RESET_HOSTS,
e com HORIZON_RESET_CONFIRMA=APAGAR_DADOS_LOCAIS.
"""

import os

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import get_engine

CONFIRMACAO = "APAGAR_DADOS_LOCAIS"
HOSTS_LOCAIS = frozenset({"localhost", "127.0.0.1", "::1"})


class ResetRecusado(RuntimeError):
    pass


def validar_alvo(
    url: str,
    ambiente: str,
    confirmacao: str,
    hosts_extra: str = "",
) -> None:
    if ambiente == "production":
        raise ResetRecusado("APP_ENV=production")
    if confirmacao != CONFIRMACAO:
        raise ResetRecusado(f"defina HORIZON_RESET_CONFIRMA={CONFIRMACAO}")
    if not url.strip():
        raise ResetRecusado("DATABASE_URL vazia")
    alvo = make_url(url)
    if alvo.get_backend_name() == "sqlite":
        return
    permitidos = HOSTS_LOCAIS | {
        host.strip().lower() for host in hosts_extra.split(",") if host.strip()
    }
    if (alvo.host or "").lower() not in permitidos:
        raise ResetRecusado("host fora da lista local")


def main() -> None:
    try:
        validar_alvo(
            settings.database_url,
            settings.app_env,
            os.environ.get("HORIZON_RESET_CONFIRMA", ""),
            os.environ.get("HORIZON_RESET_HOSTS", ""),
        )
    except ResetRecusado as exc:
        raise SystemExit(f"reset recusado: {exc}") from None
    engine = get_engine()
    with engine.begin() as conn:
        cols = [
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='usuarios'"
                )
            )
        ]
        print("usuarios_cols_ok", "nome" in cols or "nome_completo" in cols)
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print("alembic", version)

        ti = conn.execute(
            text(
                "SELECT id, email, papel FROM usuarios "
                "WHERE papel = 'TI' AND deleted_at IS NULL"
            )
        ).all()
        print("ti_antes", len(ti))
        for row in ti:
            # só domínio/tamanho — sem vazar e-mail completo em log se preferir
            email = str(row[1])
            mascara = email[:3] + "***@" + email.split("@")[-1]
            print("ti_keep", mascara if "@" in email else "***")

        # Ordem: filhos → pais. Mantém usuários TI.
        tabelas = [
            "respostas",
            "pesquisa_participantes",
            "tokens_resposta",
            "opcoes_resposta",
            "perguntas",
            "pesquisas",
            "template_opcoes_resposta",
            "template_perguntas",
            "templates_pesquisa",
            "projeto_documentos",
            "documentos",
            "entregas_mensagem",
            "notificacoes",
            "ia_mensagens",
            "ia_conversas",
            "setores",
            "configuracoes_projeto",
            "projeto_usuarios",
            "convites",
            "pedidos_consultora",
            "projetos",
            "organizacoes",
            "controle_acesso",
            "sessoes",
            "logs_auditoria",
        ]
        existentes = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public'"
                )
            )
        }
        for tabela in tabelas:
            if tabela not in existentes:
                continue
            n = conn.execute(text(f"DELETE FROM {tabela}")).rowcount
            print("delete", tabela, n)

        # Remove usuários que não são TI
        n_users = conn.execute(
            text("DELETE FROM usuarios WHERE papel <> 'TI' OR deleted_at IS NOT NULL")
        ).rowcount
        print("delete_usuarios_nao_ti", n_users)

        restam = conn.execute(
            text("SELECT count(*) FROM usuarios WHERE deleted_at IS NULL")
        ).scalar()
        print("usuarios_restantes", restam)


if __name__ == "__main__":
    main()
