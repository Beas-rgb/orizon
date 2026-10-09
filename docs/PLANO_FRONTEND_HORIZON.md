# Plano de frontend — Horizon (revisão 1.1)

**Baseline:** `b7f37e6e475ff5401df0b60744b21955bbcea52f`  
**Não altera tela.** Descreve o que falta ver, não o que já “passou”.

## O que o snapshot mostra

- O fonte vive em `frontend/`. O Render ainda pode servir `web/app` em `/app` até a fase em que o Pages for a única entrada (`docs/DEPLOY.md`).
- Há build de Pages (`VITE_BASE=/`) e de `/app`. O doc de deploy cita `https://orizon-a0u.pages.dev`. Este Passo 0 não abriu essa URL de novo.
- Tokens em `frontend/src/styles/tokens.css`. A checagem de hex existe (`frontend/scripts/checar_hex.mjs`). Não foi rodada em 08/10.
- O contexto mestre ainda cita React antigo em `arquivo/frontend/` e telas `.html`. Isso é texto antigo. O fonte atual é o Vite. Não apagamos o contexto; a nota de 08/10 marca a seção como histórica.

## Fluxos que precisam de passagem E2E (pendente)

Nenhum item abaixo foi exercido neste Passo 0. Não marcar como corrigido.

1. Entrada abre com a API dormindo e mostra o aviso de acordar.
2. Login, primeiro acesso e link de resposta não duplicam `/app` quando `APP_PUBLIC_URL` for o Pages.
3. Consultora aplica pesquisa. Funcionário responde e vê a própria nota. Órgão vê só o consolidado.
4. CLIMA não mostra autor. Agregado respeita K=5.
5. Pessoa de outra organização não abre recurso por id (a API deve responder 404; a tela não finge sucesso).

## Estados visuais

Tela nova continua com quatro estados: carregando, vazio, erro, sem permissão. Tela que chama a API também trata servidor acordando. Isso é regra de `docs` e de `.cursor/rules`, não uma auditoria visual de 08/10.

## Sessão no navegador

`docs/SECURITY.md` descreve refresh cerca de 60 segundos antes de expirar, uma tentativa após 401, e limpeza da sessão se o refresh vier 401 ou 429. Rever isso no navegador faz parte do E2E. Não foi feito aqui.

## Aceite

Um fluxo só entra como “visto” com data, URL (Pages ou `/app`) e o que aconteceu. Sem isso, o estado é pendente.
