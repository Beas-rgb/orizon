# Pacote de planos v4 (Cursor)

**Data:** 01/10/2026 · Base histórica do pacote: `86940d3` · Hospedagem: Render Free + Neon Free

Este índice resume o pacote. Os arquivos de cada fase (`00_PLANO_MESTRE.md`, `FASE_0N_*.md`, etc.) entram aqui quando forem colados ou copiados para `docs/plano/`.

## Ordem de leitura

| Arquivo | Para quê |
|---|---|
| `00_PLANO_MESTRE.md` | Contexto, decisões, mapa de fases |
| `01_PROMPT_E_REGRAS_CURSOR.md` | Prompt e regras do Cursor |
| `FASE_00` … `FASE_10` | Uma fase por vez, PASSO 0 → aprovação → tarefa |

## Assets

- `assets/benchmark_indices.sql` — benchmark de índices **v2** (só staging, apaga dados).
- Exige: `psql "<URL>" -v ambiente=staging -v confirmo_apagar=SIM -f assets/benchmark_indices.sql`

## Decisões padrão (se você não responder outra coisa)

D1 Pages · D2 sem ping · D5 sem e-mail por resposta · D6 limite só por usuário · D7 `ENABLE_LAB` desligado em produção · D12 auditoria 365 dias.

## Honestidade

Nenhum número de capacidade sem o relatório da Fase 9. Tempos do sandbox só comparam antes/depois.
