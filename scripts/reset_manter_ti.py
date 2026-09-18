"""Limpa o banco mantendo só contas TI (dev). Não imprime URL nem senha."""

from sqlalchemy import text

from app.core.database import get_engine


def main() -> None:
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
            text("SELECT id, email, papel FROM usuarios WHERE papel = 'TI' AND deleted_at IS NULL")
        ).all()
        print("ti_antes", len(ti))
        for row in ti:
            # só domínio/tamanho — sem vazar e-mail completo em log se preferir
            email = str(row[1])
            print("ti_keep", email[:3] + "***@" + email.split("@")[-1] if "@" in email else "***")

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
            "sessoes_refresh",
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
