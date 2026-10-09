# Plano de backend — Horizon (revisão 1.1)

**Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Não implementa código.** Ordena o que o backend só pode fazer depois do P0.

## Migrations

- O git tem revisões `0001`–`0020`. `0001` a `0017` continuam intocáveis, como já diz `docs/MIGRATIONS.md`.
- Índice novo no Postgres: `CREATE INDEX CONCURRENTLY`, fora de transação, e só com `EXPLAIN` — regra já do projeto.
- Model e migration no mesmo commit, quando houver mudança de model. Este plano não cria migration.
- **Proibido até confirmar o destino do Render:** `alembic stamp`, `alembic upgrade` contra produção, `scripts/reset_manter_ti.py`.
- Experimentar só num branch de staging, com URL direta (sem `-pooler`) e com restore combinado antes. `docs/MIGRATIONS.md` já pedia branch; a revisão 1.1 acrescenta que o branch certo ainda não está amarrado ao Render.

## Autorização

Toda rota sensível continua exigindo usuário, papel global, papel no projeto, organização, projeto, estado e visibilidade. Acesso cruzado entre organizações é o teste que falta **reexecutar**, não uma feature nova. O RC descreve 404; a auditoria de setembro descreve três checagens paralelas. Enquanto a suíte não rodar de novo, isso é risco aberto, não correção declarada.

## Transações

E-mail e chamada externa ficam fora de transação aberta e fora do request de resposta. O doc de desempenho da Fase 4 afirma que a resposta não envia e-mail no request. Isso é relato do código daquela fase, não uma prova refeita em 08/10.

## Testes

A CI em `.github/workflows/ci.yml` sobe Postgres 16, aplica `alembic upgrade head` e roda `pytest`. Existir o workflow não é resultado. O próximo registro de backend precisa colar a data e o resumo real (passed/failed), ou dizer explicitamente que não rodou.

## Fora deste plano

Pool, região e capacidade não se ajustam aqui. Ver `docs/PLANO_ESCALA_VALIDACAO_50K.md`.
