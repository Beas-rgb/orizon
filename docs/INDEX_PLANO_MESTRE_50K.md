# Índice — plano mestre Horizon (revisão 1.1)

**Data:** 08/10/2026 · **Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`

Leia primeiro o relatório. Este índice não manda migration, reset, carga nem pentest em produção.

## Ordem

| # | Documento | Para quê | Portão |
|---|---|---|---|
| 0 | `docs/RELATORIO_PASSO_0_2026-10-08.md` | Baseline, o que foi lido e o que continua aberto | P0: identificar o banco do Render na tela, sem colar segredo |
| 1 | `docs/AUDITORIA_BANCO_SEGURANCA_2026-10.md` | Schema, riscos e estado da evidência | Sem `stamp`, `upgrade` em produção nem `reset_manter_ti.py` antes do P0 |
| 2 | `docs/PLANO_BACKEND_HORIZON.md` | Autorização, transação, migrations, testes | Isolamento entre organizações e CLIMA tratados como risco até reexecução |
| 3 | `docs/PLANO_FRONTEND_HORIZON.md` | Fluxos, estados visuais, sessão | Não marcar tela como corrigida sem o fluxo visto |
| 4 | `docs/PLANO_ESCALA_VALIDACAO_50K.md` | 10 mil usuários/mês, depois 50 mil | Mês não é simultaneidade. Sem número de capacidade até a corrida |
| 5 | `docs/PLANO_MESTRE_HORIZON_50K.md` | Estratégia e arquitetura que se preserva | Amarra a ordem acima |
| 6 | `docs/PLANO_GERENTE_ANALITICO_IA.md` | IA futura | Bloqueada até banco, segurança, produto e carga |

## O que este índice não substitui

- `docs/HORIZON_CONTEXTO_IA.md` — protocolo e domínio.
- `docs/plano/README.md` — pacote v4 (histórico; as fases nunca foram coladas aqui).
- `docs/AUDITORIA_2026-09.md` e `docs/PLANO_MESTRE_AUDITORIA_GROK_4_7.md` — fotos antigas.
- `docs/SECURITY.md`, `docs/PERFORMANCE.md`, `docs/MIGRATIONS.md`, `docs/DATA_MODEL.md`, `docs/DEPLOY.md`, `docs/CARGA_STAGING.md`, `docs/RELEASE_CANDIDATE.md` — operação já escrita. As notas de 08/10 no topo apontam para cá.
