# Migrations

> Nota 12/10/2026: no git o head é `0021_indices_modelo`. No working tree local existem também `0022_envio_e_tarefas` (chave de envio + tabela `tarefas`) e `0023_origem_sintetica` (marcador de laboratório). A 0021 no disco usa `CREATE INDEX CONCURRENTLY` fora de transação, como a 0018. **Nenhuma delas vai para o Neon sem autorização.** O boot (`MigracaoAdiada`) não migra banco com tabelas e sem `alembic_version`. Resposta de pesquisa usa `pg_advisory_xact_lock`.
>
> Ensaio local (container `horizon-pg-ensaio`, porta 54329, banco recriado vazio): `0001` até `0023` aplicou; drift com `compare_type` e `compare_server_default` passou; os seis índices da 0021 existem. Isso não é o Neon.
>
> Plano de aplicação da 0021 em produção (quando autorizado): (1) conferir no painel que `DATABASE_URL` e `DATABASE_URL_DIRECT` são o mesmo destino lógico, sem colar valores; (2) backup/PITR confirmados; (3) rodar `EXPLAIN` dos seis índices em staging (`scripts/explain_indices_0021.py` + `TEST_DATABASE_URL_PG` local, nunca `DATABASE_URL`); (4) janela curta com URL direta; (5) rollback = `alembic downgrade 0020_lab` só se a 0022/0023 ainda não tiverem sido aplicadas. Não usar `stamp`.
>
> Nota 08/10/2026: no git o head era `0020_lab` (`migrations/versions/`). Isso não prova a revisão do Neon. Não aplicar `alembic stamp` nem `alembic upgrade` no destino do Render até o P0 em `docs/RELATORIO_PASSO_0_2026-10-08.md`. Staging só com restore combinado e URL direta. Estado vivo: `docs/INDEX_PLANO_MESTRE_50K.md`.

- Nova mudança de tabela é um arquivo Alembic novo. 0001 a 0017 não são editados.
- Índice no Postgres nasce com `CREATE INDEX CONCURRENTLY`, fora de transação.
- O downgrade remove só o que a migration criou.
- O model e a migration vão no mesmo commit.
- O teste de drift compara o banco com os models. Ele só roda se `TEST_DATABASE_URL_PG` estiver definido.
- No CI o job sobe Postgres 16, roda `alembic upgrade head` e depois `pytest`.

Para experimentar no branch de staging do Neon, use a URL direta (sem `-pooler`) em `DATABASE_URL` e rode `alembic upgrade head`. Não rode isso no banco de produção sem um branch.
