# Relatório inicial — Passo 0 (08/10/2026)

**Revisão documental:** 1.1  
**Baseline de código:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Repositório:** https://github.com/Beas-rgb/orizon  
**O que este arquivo é:** fonte de verdade do baseline, das incertezas e da primeira ação operacional.

Este Passo 0 **não** executou a suíte de testes, migration, reset, seed, pentest nem carga. **Não** leu `DATABASE_URL` do Render. **Não** consultou o Neon nesta etapa.

O arquivo `HORIZON_DOCUMENTACAO_PASSO0_REV_1_1.patch` não estava no clone. O texto abaixo junta a capa da revisão 1.1 com o que se confere lendo o git em `b7f37e6`. Onde o dossiê citado na capa não veio no patch, o item fica **pendente**. Não há diferença de coluna inventada.

## Três estados

| Estado | Significado |
|---|---|
| Verificado no snapshot | Arquivo ou commit lido neste Passo 0. Não é teste executado. |
| Relatado | Afirmação da capa 1.1 ou de um doc antigo. Não reproduzida aqui. |
| Pendente | Ainda precisa de tela, staging ou suíte. |

## Verificado no snapshot `b7f37e6`

- `HEAD` local coincide com o SHA acima.
- Migrations no git: `0001` a `0020` (`migrations/versions/0020_lab.py` inclusive). Isso não prova que o Neon está nessa revisão.
- Suíte de CI existe em `.github/workflows/ci.yml` (Postgres 16, `alembic upgrade head`, `pytest`, `ruff`, frontend). **Não foi executada** neste Passo 0.
- `scripts/reset_manter_ti.py` existe. Não foi rodado.
- Testes citados no RC existem como arquivo: `tests/test_anonimato_clima.py`, `tests/test_matriz_seguranca_rc.py`. Existir o arquivo não é tê-los rodado em 08/10.
- `docs/DEPLOY.md` anota Neon em `aws-sa-east-1` e uma branch `staging` em 02/10/2026. Isso descreve um projeto visto na API Neon naquele dia. Não identifica o banco do Render.
- `docs/PERFORMANCE.md` registra cerca de 689 ms em `GET /health/db` em 02/10/2026. É uma medição pontual. Não é capacidade.
- A tabela de carga em `docs/PERFORMANCE.md` está vazia.

## Relatado, não reproduzido aqui

- Lista de 22 tabelas no Neon, vinda do dossiê da capa. Não está comprovado que esse inventário é o banco apontado pelo Render.
- O contexto mestre ainda fala em 21 tabelas de um dump antigo (`docs/HORIZON_CONTEXTO_IA.md`). Os dois números não foram recontados neste Passo 0.
- Auditoria de 18/09 descreve pool 2/0. `docs/PERFORMANCE.md` descreve pool 5+5 numa data posterior. São fotos diferentes. Nenhuma foi relida no painel do Render hoje.
- Anonimato de CLIMA: a auditoria de setembro chama o anonimato de cosmético; o diário posterior diz que o elo do token é cortado e K=5. Os dois textos continuam no repositório. Este Passo 0 não reexecutou o teste.

## Pendente (P0 primeiro)

1. Na tela do Render, conferir se `DATABASE_URL` e `DATABASE_URL_DIRECT` apontam para o projeto Neon esperado. Sem copiar senha nem connection string para issue, log, chat ou commit.
2. Só depois: estratégia de recuperação e restore em staging. Até lá, não usar `alembic stamp`, `alembic upgrade` no destino de produção, nem `scripts/reset_manter_ti.py`.
3. Região do serviço Render (o header de `/health` não a expõe).
4. Rodar a suíte CI e registrar o resultado de verdade.
5. `TRUSTED_PROXY_HOPS` segue 0 até a conta TI comparar o IP.
6. `APP_PUBLIC_URL` e `CORS_ORIGINS` no Render ainda estão como passo manual em `docs/DEPLOY.md`.

## Ordem que este relatório impõe

Reconciliar o banco, depois segurança crítica, integridade do backend, fluxos E2E, frontend, carga e, por último, o Gerente Analítico. Índice: `docs/INDEX_PLANO_MESTRE_50K.md`.
