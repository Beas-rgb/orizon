# Release Candidate — 10/10

Checklist da seção 9 de `docs/HORIZON_CONTEXTO_IA.md` para o boot.

## O que o consultor usa agora

1. **Árvore** — aba Estrutura do trabalho: expandir, recolher, busca em
   qualquer nível, cargo e setor no nó. API: `GET /projetos/{id}/arvore`.
2. **Importação** — aba Participantes: modelo CSV, prévia, confirmação
   atômica. API: `POST /projetos/{id}/importar/previa` e `/confirmar`.
3. **Editor de desempenho** — abas Geral, Estrutura, Participantes,
   Perguntas, Perspectivas, Pesos, Regras, Prévia, Aplicação, Resultados,
   Histórico. Pesos numéricos no ciclo (`PATCH /ciclos/{id}`). CLIMA não
   ganha ciclo.

## Segurança (matriz A→B)

| Quem | Recurso de outro projeto | Esperado |
|---|---|---|
| Consultora B | árvore / importar / ciclos de A | 404 |
| Órgão A | árvore / ciclos de B | 404 |
| Funcionário A | árvore de A ou B, gerar relações | 404 |
| Órgão A | árvore do próprio projeto | 200 |

Testes: `tests/test_matriz_seguranca_rc.py`, `tests/test_paineis_escopo.py`,
`tests/test_anonimato_clima.py`.

## Concorrência

Dois POST seguidos: resposta → 409; publicar → 422; relações e vínculo →
idempotentes, sem linha duplicada. Dois POST em paralelo: sem 500.
`tests/test_concorrencia.py`.

## Contas e carga (staging)

- Dataset: 32 funcionários (`scripts/contas_staging.py`). Exige
  `HORIZON_AMBIENTE=staging`. Prova local: `tests/test_dataset_boot.py`.
- Carga: `scripts/carga_staging.py`. Recusa produção. Ver
  `docs/CARGA_STAGING.md`.

## CLIMA

Intacto. K=5, token desligado da resposta, painel agregado. Não há tabela
`RespostaAnonima` nova — o elo já é zerado.

## Sem feature nova no Dia 15

Este RC fecha tela + teste. Sem OKR, sem feed, sem clone de RH.
