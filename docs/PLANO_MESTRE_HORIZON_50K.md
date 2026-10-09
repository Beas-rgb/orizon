# Plano mestre Horizon — revisão 1.1

**Data:** 08/10/2026  
**Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Fonte do que está aberto:** `docs/RELATORIO_PASSO_0_2026-10-08.md`

## O que se preserva

A arquitetura continua: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL no Neon, Cloudflare R2, React/Vite. Hash Argon2id. Soft delete. Autorização por usuário, papel global, papel no projeto, organização, projeto, estado e visibilidade. IDOR responde 404. CLIMA com K=5. IA desativada no baseline. Hospedagem atual descrita nos docs: Render Free + Neon Free, tela também no Cloudflare Pages. Sem ping de manutenção.

O produto desta etapa continua o da pesquisa: a consultora aplica, o funcionário responde e vê a própria nota, o órgão consulta o consolidado. OKR e feedback do Yespper ficam de fora.

## O que esta revisão muda na ordem

A ordem antiga de “fase concluída” no contexto mestre não autoriza o próximo módulo de IA nem uma afirmação de escala. A execução passa a ser:

1. Reconciliar qual banco o Render usa.
2. Segurança crítica (isolamento, CLIMA, sessão).
3. Integridade do backend (migrations, transações, testes de verdade).
4. Fluxos ponta a ponta.
5. Frontend (estados e sessão no navegador).
6. Carga, no staging, com o primeiro cenário mensal.
7. Gerente Analítico, só depois desses portões.

## Escala, sem confundir unidade

- **10 mil usuários por mês** é o primeiro cenário de validação. Ainda não foi medido.
- **50 mil usuários por mês** só entra depois de evidência do cenário anterior.
- Nenhum dos dois números é usuários simultâneos. Simultaneidade continua um ensaio à parte (`docs/CARGA_STAGING.md`), e a tabela de resultados em `docs/PERFORMANCE.md` está vazia.
- Este plano não declara que o Render ou o Neon “aguentam” esses volumes.

## Banco

O destino efetivo de `DATABASE_URL` / `DATABASE_URL_DIRECT` está **P0 aberto**. Migrations no git vão até `0020`. Isso é o repositório, não o Neon de produção. Recuperação e restore em staging vêm antes de qualquer `upgrade` no destino real.

## IA

`ia_modo` permanece desativada. O desenho do Gerente está em `docs/PLANO_GERENTE_ANALITICO_IA.md` e não autoriza implementação neste baseline.
