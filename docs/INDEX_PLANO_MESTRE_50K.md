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

## Estado em 12/10/2026

- `master` está em `aa8d91e` (merge do PR #2). O CI passou nesse commit. Isso não prova o banco do Render.
- Head Alembic **no git:** `0021_indices_modelo`. No working tree local (ainda sem commit): `0022_envio_e_tarefas` e `0023_origem_sintetica`. A 0021 no disco passou a `CREATE INDEX CONCURRENTLY` fora de transação. **Não aplicar nenhuma delas em produção** sem autorização e plano de rollback.
- Boot (`app/core/migracao.py`): revisão desconhecida, malformada, duplicada ou anterior sem allowlist bloqueia sem `upgrade` (`decidir()`). Banco com tabelas e sem `alembic_version` não migra e deixa a API subir (`MigracaoAdiada`). `/health/ready` compara a revisão com o head e recusa escrita.
- Resposta de pesquisa: `pg_advisory_xact_lock` por pesquisa e funcionário (`app/services/pesquisa/resposta.py`).
- Pacote do Opus 5.5: fonte íntegra é `C:\Users\jbiel\Downloads\HORIZON_PACOTE_UNICO_OPUS_5_5.zip` (SHA-256 `5d765c37…`, 178 entradas). A cópia `HORIZON_PACOTE_UNICO_OPUS_5_5_ATUALIZADO.zip` tem 179 entradas, adendo em `01_BRIEF/` e a nota no prompt; `testzip` limpo e hashes do manifesto conferidos. **Não usar `docs/opus/` como fonte** (arquivos com nomes trocados). Não versionar essa pasta sem aprovação.
- A regra do Cursor cita `docs/plano/00_PLANO_MESTRE.md`, que **não existe**. O índice vigente é este arquivo.

## Regressões de 10/10 — refeitas localmente (sem commit)

Em 10/10 existiam no disco, e depois sumiram do Git e da árvore: o reconciliador do legado, a guarda de revisão Alembic e 18 `server_default` nos modelos. Decisão: **refazer os três**, sem `stamp` em produção.

| Item | Onde | Estado local |
|---|---|---|
| Guarda de revisão | `app/core/migracao.py` (`decidir`, `mapa_revisoes`, `MIGRACAO_ORIGENS_AUTORIZADAS`) | Refeita. Revisão fora do grafo ou não autorizada não chama `upgrade`. |
| 18 `server_default` | `pesquisa.py`, `configuracao.py`, `controle_acesso.py`, `documento.py`, `lab.py` (além dos 8 já alinhados) | Recolocados nos modelos. Drift com `compare_server_default` no PG local. |
| Reconciliador | `app/core/reconciliacao_legado.py` | Só cópia isolada (`RECONCILIAR_URL` + `COPIA_ISOLADA`). Nunca `stamp` sem equivalência completa. |

## O que este índice não substitui

- `docs/HORIZON_CONTEXTO_IA.md` — protocolo e domínio.
- `docs/plano/README.md` — pacote v4 (histórico; as fases nunca foram coladas aqui).
- `docs/AUDITORIA_2026-09.md` e `docs/PLANO_MESTRE_AUDITORIA_GROK_4_7.md` — fotos antigas.
- `docs/SECURITY.md`, `docs/PERFORMANCE.md`, `docs/MIGRATIONS.md`, `docs/DATA_MODEL.md`, `docs/DEPLOY.md`, `docs/CARGA_STAGING.md`, `docs/RELEASE_CANDIDATE.md` — operação já escrita. As notas de 08/10 no topo apontam para cá.
- `docs/TELAS_FRONTEND.md` — matriz 01–93 e peso morto (sem remoção).
- `docs/LAB_ARQUITETURA.md` — decisão C do laboratório.
- `docs/FASES_5_7.md` — testes, metas S0–S9 e critérios do piloto.
