# Auditoria crítica Horizon — 18/09/2026

Documento vivo de riscos, correções e roadmap. Escrito para ser lido por
uma pressa (CTO/sócio técnico), não por um mentor. Tom: o que falha, o que
já foi fechado, o que falta, em que ordem.

**Repo:** https://github.com/Beas-rgb/orizon.git  
**Baseline de testes no dia:** 73 → 79 passed (após as correções desta data).  
**Escopo lido:** `app/`, `migrations/`, `tests/`, `render.yaml`, `Dockerfile`,
`frontend/` (só o necessário para o SPA).

---

## 0. Veredito em uma página

O Horizon **já tem um backend utilizável** para demo e para o fluxo
consultora → pesquisa → funcionário → órgão. Os testes cobrem o que a
documentação promete (isolamento entre órgãos, resposta autenticada,
editor de rascunho, mídia). Isso **não** significa que o produto está
pronto para produção com dados reais de clima organizacional.

Três verdades duras:

1. **O "anonimato" do clima é cosmético.** A API não devolve o nome
   de quem respondeu, mas o banco liga resposta → token pessoal →
   `usuario_id`. A consultora ainda vê nome + e-mail + status
   (`PENDENTE` / `EM_ANDAMENTO` / `RESPONDIDA`) em
   `/pesquisas/{id}/participantes`. Com N=1 ou N=2 no painel, a média
   **é** a resposta da pessoa. Prometer anonimato assim é mentira
   operacional — e, em clima, é o tipo de mentira que gera processo.
2. **A autorização está espalhada em três implementações paralelas**
   (`_participa`, `_papel`, `_papel_no_projeto`). Já divergem (TI recebe
   403 em projetos e 404 em pesquisas; mídia de pergunta em RASCUNHO
   baixa para órgão/funcionário). Cada correção futura em um service
   **não** propaga aos outros. Isso é o padrão clássico de vulnerabilidade
   por colisão de funções.
3. **O banco aguenta demo, não carga.** `DB_POOL_SIZE=2` +
   `DB_MAX_OVERFLOW=0` + 1 worker uvicorn + e-mail SendGrid **dentro**
   do request = ~2 usuários simultâneos reais. Com 20, a fila estoura.
   O painel faz ~75 queries por pesquisa típica (N+1).

O que **já está certo** e não precisa ser refeito: Argon2id para senha
(nunca texto puro), JWT com secret obrigatório, access curto (15 min),
refresh com hash no banco, token de e-mail com SHA-256, soft delete
respeitado na maioria das queries, IDOR cross-projeto → 404 nos fluxos
testados, log de acesso sem corpo/token, MIME real na mídia de pergunta.

---

## 1. O que foi corrigido nesta data (já no código)

Três buracos fechados **antes** deste documento. Sem eles, o restante
da auditoria seria teatro.

| # | Gravidade | Problema | Evidência | Correção |
|---|-----------|----------|-----------|----------|
| C1 | **CRÍTICO** | Path traversal no SPA: `GET /app/..%2f..%2f.env` devolvia **200** com o conteúdo do `.env` (JWT_SECRET, DATABASE_URL, chaves R2/SendGrid, ADMIN_SENHA). Sem autenticação. | `app/main.py` antigo + prova empírica no TestClient | `_arquivo_do_build()` confina o pedido com `Path.resolve()` + `is_relative_to(web/app)`. |
| C2 | **CRÍTICO** | Biblioteca confiava no `Content-Type` do navegador. HTML/JS disfarçado de PDF entrava. | `app/integrations/arquivos.py:_validar` vs `detectar_mime` (só mídia) | Validação por assinatura de bytes (`%PDF-`, `PK\x03\x04`, magic de imagem) + rejeição de HTML rotulado como texto. Header `X-Content-Type-Options: nosniff` no download. |
| C3 | **ALTO** | Em produção, `JWT_SECRET`/`DATABASE_URL` vazios só falhavam na 1ª requisição, com 500 opaco. | `app/core/config.py`, `tokens.py` | `conferir_producao()` no boot de `app/main.py`. |

Regressão: `tests/test_seguranca_arquivos.py` (6 casos). Suite: **79 passed**.

> **Impacto em produção (Render):** o `.env` **não** entra na imagem
> Docker (`.dockerignore` + vars `sync: false` no `render.yaml`). O
> buraco C1 era mortal em máquina local / staging com `.env` no disco
> ao lado do código. Em produção, o mesmo código ainda permitiria
> ler qualquer arquivo com ponto fora de `web/app` (ex.: `pyproject.toml`,
> dumps esquecidos). A correção vale nos dois ambientes.

---

## 2. Prioridade imediata — backend (antes de qualquer feature)

Ordem sugerida. Cada item é **ação**, não desejo.

### P0 — fechar antes do próximo deploy com dados reais

| ID | O quê | Por quê | Como (esboço) | Teste mínimo |
|----|-------|---------|---------------|--------------|
| P0.1 | Desabilitar `/auth/bootstrap` em produção | Qualquer um que chegar na tabela vazia vira TI com JWT. Corrida de deploy / Neon resetado = conta sequestrada. | Exigir `BOOTSTRAP_SECRET` one-time no body **ou** remover a rota quando `APP_ENV=production` (TI nasce só via `ADMIN_*`). | Teste: em `app_env=production`, `POST /auth/bootstrap` → 404. |
| P0.2 | Quebrar o vínculo resposta ↔ usuário em CLIMA | Hoje `respostas.token_id` → `pesquisa_participantes.token_id` → `usuario_id`. JOIN trivial. | Para tipos anônimos: gravar respostas num token de submissão **sem** FK para participante; ou rotacionar `token_id` após o submit e zerar o vínculo. Manter `pesquisa_participantes` só com status agregado. | Teste: consultora com SQL direto **não** consegue juntar resposta a pessoa. Teste de painel com N=1. |
| P0.3 | Remover `/participantes` nominal em CLIMA | A consultora vê quem respondeu / está respondendo. Antítese de anonimato. | Em CLIMA: devolver só `{respondidas: 12, total: 30}`. Sem nome, e-mail, status individual, `EM_ANDAMENTO`. | Teste: payload de CLIMA sem campos de identidade. |
| P0.4 | k-anonimato no `painel()` | Com 1 respondente, `media` = resposta da pessoa. | Se `distinct(token_id) < K` (K=5 sugerido), omitir `media`/`contagem_opcoes` e marcar `suprimido: true`. | Teste: N=1 → painel sem média; N=5 → média ok. |
| P0.5 | Unificar autorização num módulo | Três funções fazem a mesma checagem e já divergem. | Extrair `app/core/autorizacao.py` com `exigir_papel(db, usuario, projeto_id, papeis, operacao)` → 404. Migrar `projeto`, `pesquisa`, `biblioteca`. | Testes de escopo existentes continuam verdes + 1 caso de mídia em RASCUNHO. |

### P1 — curto prazo (1–2 sprints de backend)

| ID | O quê | Por quê |
|----|-------|---------|
| P1.1 | Hash dos tokens de pesquisa no banco (como convites) | Hoje `tokens_resposta.token` fica em claro; dump do Neon = todos os links. |
| P1.2 | Access token sobrevive ao logout / troca de senha | `sair` só revoga refresh. Incluir `jti` ou `sessao_id` no JWT e validar no `usuario_atual`. |
| P1.3 | `baixar_midia_pergunta` exige pesquisa PUBLICADA/ENCERRADA para órgão/funcionário | Hoje baixa mídia de RASCUNHO. |
| P1.4 | Rate limit em `cadastro-consultora`, `primeiro-acesso`, `redefinir-senha` (IP + e-mail) | Hoje só login/recuperar/convite limitam. |
| P1.5 | Não devolver `link_primeiro_acesso` quando `APP_ENV=production` | Falha de SMTP não pode vazar token no JSON. |
| P1.6 | Respostas 404 uniformes (TI em projetos também) | 403 vs 404 enumera existência. |
| P1.7 | Índices: `respostas(pergunta_id)`, `respostas(opcao_id)`, `projetos(consultor_id)`, `pesquisas(projeto_id, status)` | Painel e listagens fazem full scan. Migration Alembic reversível. |
| P1.8 | Reescrever `painel()` em 1–2 queries agregadas | Hoje ~75 queries / pesquisa típica. |
| P1.9 | E-mail fora do request (`BackgroundTasks` mínimo ou fila) | Publicar pesquisa com 3 órgãos segura o pool por até 60 s. |
| P1.10 | Auditoria de resposta de CLIMA **sem** `usuario_id` | `PESQUISA_RESPONDIDA` hoje grava quem respondeu. |

### P2 — endurecimento / limpeza

- Paginação em notificações, entregas, listagens.
- Remover side effects em GET (`garantir_rotulos`, criar participante em `listar_minhas_pesquisas`).
- Dividir `pesquisa.py` (~1400 linhas) e `identidade.py` (~950) em módulos por responsabilidade.
- Extrair `_auditar` (4 cópias) e `_chamar` (6 routers).
- Timeout no Mailtrap e no cliente R2/boto3.
- Documentar na `.env.example` o host `-pooler.neon.tech`.
- Fail-fast: validar `JWT_SECRET` forte (≥32 chars) no boot.
- Observabilidade: log JSON + `request_id`; métrica de conexões do pool.

---

## 3. Senhas e armazenamento — o que está bem e o que falta

### Bem

- Hash **Argon2id** via `passlib` (`app/core/security.py`). Senha nunca
  volta em resposta, log ou e-mail.
- Regra de senha no backend (mínimo 8, maiúscula, número, especial,
  sem espaço nas pontas) — a tela não decide.
- Token de e-mail (convite / redefinição / 1º acesso) é **opaco**
  (`secrets.token_urlsafe`); no banco fica só SHA-256.
- Refresh token idem: só hash em `sessoes`.
- Login: mensagem uniforme + verify dummy contra timing
  (`identidade.py`).
- Rate limit de login: 3 erros → 5 min, por e-mail normalizado.

### Falta / risco

| Risco | Detalhe |
|-------|---------|
| Access JWT pós-logout | Continua válido até `exp` (15 min). Roubo de token = janela aberta. |
| Token de pesquisa em claro | Diferente dos convites. Dump = todos os links. |
| `link_primeiro_acesso` no JSON | Em development / falha de e-mail, o token aparece na resposta HTTP (útil em local; perigoso se `APP_ENV` errado em produção). |
| Argon2 default do passlib | Não há `time_cost`/`memory_cost` explícitos. Em Render free, login é ~50–300 ms CPU; sob pico, satura. Tunar depois de medir. |
| Bootstrap público | Cria TI sem autenticação prévia se a tabela estiver vazia. |

**Processo:** toda mutação de senha (redefinir, 1º acesso) deve
**revogar sessões** (já faz no refresh) **e** invalidar access tokens
ativos (ainda não faz).

---

## 4. Pesquisa de clima — anonimato real vs. o que o código faz

### O que o código faz hoje

- Funcionário **precisa estar autenticado** para responder.
- Cada resposta grava `token_id` de um token **pessoal** criado em
  `_participante_da_pesquisa`.
- `pesquisa_participantes` liga `usuario_id` ↔ `token_id` ↔ status.
- Painel devolve só agregados (sem nome) — bom na superfície.
- CLIMA não devolve a nota individual na API; DESEMPENHO devolve.
  **A diferença é só na resposta HTTP**, não no modelo de dados.
- `/participantes` devolve nome, e-mail e status por pessoa.
- Abrir o formulário marca `EM_ANDAMENTO` — a consultora vê quem está
  preenchendo **antes** do submit.
- Auditoria `PESQUISA_RESPONDIDA` grava `usuario_id`.
- Timestamps iguais em `respostas`, `tokens_resposta` e
  `pesquisa_participantes` facilitam correlação.
- `TEXTO_LIVRE` é aceito em CLIMA e fica no banco com vínculo
  reidentificável (o painel hoje não mostra o texto — mas o dado existe).
- Sem piso de k-anonimato: N=1 revela a resposta.

### O que precisa ser verdade para prometer anonimato

1. **Não existir caminho JOIN** de resposta → pessoa no banco, para
   tipos anônimos (CLIMA, e eventualmente CARGOS_SALARIOS).
2. **Consultora não vê** quem respondeu / está respondendo — só
   contagem agregada.
3. **Painel suprime** agregados quando N < K.
4. **TEXTO_LIVRE** ou é proibido em CLIMA, ou vai para bucket
   separado sem chave reversível, revisado manualmente.
5. **Documentação e README** param de falar em "token anônimo" se a
   resposta exige login. Ou o fluxo muda, ou o texto muda. Hoje os
   dois contradizem um ao outro.

Até P0.2–P0.4 estarem feitos, o produto deve ser descrito internamente
como **"resposta autenticada com painel agregado"**, não como
"pesquisa anônima". Vender anonimato sem isso é risco jurídico, não só
técnico.

---

## 5. Autorização — colisões e processo

### Funções que fazem a "mesma" coisa e já divergem

| Função | Onde | Retorno | Fraqueza observada |
|--------|------|---------|--------------------|
| `_participa` | `projeto.py` | `bool` | TI → 403 (quebra a regra "IDOR = 404") |
| `_papel` | `pesquisa.py` | `str \| None` | Não checa status da pesquisa / `pesquisas_habilitadas` |
| `_papel_no_projeto` | `biblioteca.py` | `str \| None` | Cópia de `_papel` + `pode_ver` |

**Colisão concreta já explorável:** `listar_perguntas_pesquisa` exige
CONSULTOR; `baixar_midia_pergunta` abre para ORGAO/FUNCIONARIO **sem**
checar se a pesquisa ainda é RASCUNHO. Mesmo domínio, políticas
diferentes.

### Processo obrigatório daqui pra frente

1. **Uma** função de autorização no core. Services só chamam.
2. Toda rota sensível: autenticação + papel global + papel no projeto
   + organização + projeto + estado do recurso + operação.
3. IDOR → **sempre 404**. Teste de acesso cruzado entre organizações
   em todo módulo novo (já existe padrão em `test_paineis_escopo.py`).
4. Checklist da seção 9 de `docs/HORIZON_CONTEXTO_IA.md` **antes** de
   marcar módulo pronto — não depois.

---

## 6. Banco e carga — o que quebra com gente de verdade

| Cenário | Comportamento hoje |
|---------|-------------------|
| 3 requests leves simultâneos | OK |
| 20 requests simultâneos | ~18 na fila do pool (timeout ~30 s) |
| 5 logins simultâneos | 2 processam; resto espera + ~200 ms Argon2 |
| Publicar pesquisa (200 func., 3 órgãos) | ~200 queries + e-mails inline (até 60 s) |
| Abrir painel 15 perguntas × 4 opções | ~75 queries |
| Render free + scale-to-zero | 1ª request: cold Neon + boot |

Config atual (`render.yaml`): `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=0`,
1 processo uvicorn, migrations no `CMD` do Docker.

### Barato e já

1. Subir pool para 5–10 **se** a cota Neon permitir; medir conexões.
2. Índices listados em P1.7.
3. Paginação default 50 em notificações/entregas.
4. Timeout Mailtrap + boto3.
5. Remover `garantir_rotulos()` de GET.
6. Batch de opções no router (`WHERE pergunta_id IN (...)`).

### Refatoração maior

1. E-mail/R2/CNPJ fora do request.
2. `painel()` em SQL agregado.
3. Eager loading / joins nas listagens (hoje: **zero**
   `selectinload`/`joinedload` no repo).
4. Workers uvicorn >1 **somente** com Neon pooler (`-pooler.neon.tech`)
   — senão multiplica conexões.
5. Dividir services gigantes.

---

## 7. Otimização e limpeza do backend

O código não está "pesado" por excesso de dependências. Está **pesado
por concentração e por I/O síncrono no request**.

### Enxugar (ordem)

1. Extrair `_auditar` → `app/services/auditoria.py`.
2. Extrair `_chamar` → helper/decorator de router.
3. Quebrar `pesquisa.py` em: crud, resposta, painel, mídia, modelos.
4. Quebrar `identidade.py` em: auth, convites, pedidos_consultora.
5. Mover `vincular_aceite` para módulo neutro (quebra ciclo
   identidade ↔ projeto).
6. Eliminar side effects em GET.
7. Tipar e documentar a matriz de autorização por tipo de pesquisa
   (CLIMA anônimo vs DESEMPENHO identificado) **no código**, não só
   no README.

Não reescrever a stack. Não trocar FastAPI/SQLAlchemy/Neon. O ganho
está em **menos voltas** (menos queries, menos I/O no request, uma
autorização só), não em framework novo.

---

## 8. Usabilidade — Horizon vs Yespper vs Leel

Comparação **crítica**, sem bajulação. Yespper e Leel são referências
de mercado em RH/engajamento; o Horizon, nesta etapa, é ferramenta de
**consultora aplicando pesquisa**, não clone de OKR/feedback.

### Onde o Horizon já diferencia (e deve manter)

- Fluxo consultora → órgão → funcionário com isolamento por projeto.
- Papéis claros (TI autoriza consultora; consultora não nasce sozinha).
- Nota individual só quando o tipo de pesquisa pede (desempenho).
- Escopo de produto deliberadamente estreito: **não** copiar feed,
  OKR, competências, social agora (`HORIZON_CONTEXTO_IA.md` §6–7).

### Onde Yespper costuma ganhar (e o que isso significa aqui)

| Ponto | Yespper (típico) | Horizon hoje | O que fazer **depois** do P0/P1 |
|-------|------------------|--------------|--------------------------------|
| Ciclo contínuo (OKR, check-in, feedback) | Núcleo do produto | Fora de escopo | Só depois do clima estar sólido e anônimo de verdade |
| Onboarding guiado | Passo a passo, vazios com CTA | Telas existem; pouco guia | Empty states + checklist "próximo passo" no painel |
| Notificações acionáveis | Deep link para a tarefa | Notificação genérica ("Nova resposta") | Ligar notificação → tela certa; lote em CLIMA |
| Mobile | App / PWA maduro | React responsivo básico | Auditar fluxo responder no celular (é o caminho crítico) |

**Não** adicionar OKR/feedback para "ficar igual". Isso dilui o que o
Horizon é e atrasa o que ainda está furado (anonimato, autorização).

### Onde Leel (e similares de clima/engajamento) costuma ganhar em usabilidade

| Ponto | Prática comum | Horizon hoje | Melhoria concreta |
|-------|---------------|--------------|-------------------|
| Promessa de anonimato crível | UI + modelo de dados alinhados; k-anonimato | UI agregada, modelo reidentificável | P0.2–P0.4 **antes** de qualquer campanha de marketing |
| Tempo para primeira resposta | Link curto, poucos cliques, mobile-first | Login + token + formulário | Medir cliques do e-mail até submit; cortar fricção |
| Progresso da campanha | "% responderam" sem expor quem | Lista nominal de participantes | Só contagem + meta; lembrete em lote |
| Leitura do resultado | Heatmap, filtros por setor com piso K | Painel tabular simples | Setor + k-anonimato; depois visual |
| Confiança do respondente | Texto claro "você não será identificado" | Promessa implícita, contradita pelo modelo | Texto honesto alinhado ao que o banco realmente faz |
| Acessibilidade / linguagem | Linguagem simples, contraste, teclado | Design Figma bonito; a11y ainda não auditada | Passar axe/Lighthouse nas telas de login e responder |

### Dívida de UX do próprio Horizon (independente de concorrente)

1. Dois modos de front (`frontend/` em Vite vs `web/app/` servido pela
   API) — ok para dev, confuso se não documentar o build no deploy.
2. Painel do TI mistura diagnóstico operacional com autorização de
   contas — funciona, mas um operador novo se perde.
3. Erros da API às vezes genéricos demais na UI ("não autenticado")
   e às vezes específicos demais no JSON (enumeração de e-mail em
   cadastro/convite).
4. Fluxo de 1º acesso depende de e-mail real; em local o TI precisa
   saber olhar o painel / outbox — melhorou, ainda não é óbvio.

**Regra:** usabilidade nova só entra depois que P0 de segurança e
anonimato estiver fechado. Bonito por cima de buraco é pior que
feio e correto.

---

## 9. Acesso de teste do TI para produção

Objetivo: o TI validar o sistema **sem** usar a conta de produção
nem dados reais de clima.

### Proposta (mínima e segura)

1. **Ambiente de staging** (branch Neon + serviço Render separado, ou
   branch `staging` com `APP_ENV=staging`).
2. Conta TI de staging criada via `ADMIN_*` do ambiente de staging —
   **nunca** compartilhada com produção.
3. Seed determinístico (`scripts/seed_staging.py`): 1 consultora, 1
   órgão, 3 funcionários, 1 pesquisa CLIMA publicada com respostas
   sintéticas **sem** PII real.
4. Flag `MODO_DEMO=1` que:
   - bloqueia envio de e-mail para fora de um domínio allowlist;
   - mascara e-mails na UI do TI (`j***@exemplo.gov.br`);
   - impede exportação em massa.
5. Checklist de smoke pós-deploy (manual ou script):
   - `/health` e `/health/db`
   - login TI / consultora / órgão / funcionário
   - criar projeto → publicar pesquisa → responder → painel
   - tentativa cross-orgão → 404
6. **Proibido em produção:** bootstrap público, `link_primeiro_acesso`
   no JSON, `APP_ENV=development`, seed com dados reais de cliente.

Enquanto não houver staging, o "acesso de teste" é a conta TI local
+ Mailtrap/outbox — e isso **não** substitui staging.

---

## 10. Futuras aplicações (depois do alicerce)

Ordem sugerida **só depois** de P0 + fatia relevante de P1:

1. **Setores com k-anonimato** — hoje `setor_id` existe e não é usado.
2. **Lembretes em lote** e campanhas com meta de resposta.
3. **Exportação** (CSV/PDF) do painel com as mesmas regras de
   supressão do k-anonimato.
4. **PWA / instalar no celular** do funcionário.
5. **Assinatura de entregáveis** / evidências para o órgão (além da
   biblioteca atual).
6. **Multi-consultora na mesma organização** (hoje o modelo é
   consultora dona do projeto).
7. **OKR / feedback / competências** — só quando o núcleo de pesquisa
   estiver sólido. Copiar Yespper antes disso é dispersão.
8. **IA (fase 6)** — continua suspensa (`ia_modo = DESATIVADA`) até
   haver dado limpo e política de privacidade clara.

---

## 11. Processo de correção (como trabalhar daqui)

1. **Uma prioridade por PR.** Não misturar anonimato com UI nova.
2. Protocolo do projeto: PLANO → confirmação → passos pequenos →
   testes → checklist §9 → resumo.
3. Todo P0/P1 nasce com teste que falha antes e passa depois.
4. Migration Alembic reversível; **nunca** `create_all` em produção;
   **nunca** apagar dado do Neon "para testar".
5. Ruff limpo em `app/` + `pytest` verde antes do commit.
6. Em dúvida entre feature e correção de autorização/anonimato:
   **correção ganha**.

---

## 12. Checklist rápido do estado (18/09/2026)

| Área | Estado | Nota |
|------|--------|------|
| Senha (Argon2id) | OK | Tunar custo depois de medir |
| Tokens de e-mail (hash) | OK | — |
| Tokens de pesquisa | FRÁGIL | Em claro no banco |
| JWT access pós-logout | FRÁGIL | Janela de 15 min |
| Bootstrap em produção | FRÁGIL | P0.1 |
| Path traversal SPA | **CORRIGIDO** | C1 |
| MIME biblioteca | **CORRIGIDO** | C2 |
| Boot sem secret em prod | **CORRIGIDO** | C3 |
| Autorização unificada | AUSENTE | 3 implementações |
| Anonimato clima (modelo) | FALHO | Pseudônimo reidentificável |
| k-anonimato no painel | AUSENTE | N=1 revela |
| Pool / carga | FRÁGIL | 2 conexões |
| N+1 / painel | FRÁGIL | ~75 queries |
| E-mail no request | FRÁGIL | Bloqueia pool |
| Testes automatizados | OK | 79 passed |
| Staging / acesso TI prod | AUSENTE | Seção 9 |
| Front React | OK para demo | UX fina depois do P0 |

---

## 13. Resumo para quem só lê o final

O Horizon não é um projeto ruim. É um MVP com **base sólida em
criptografia de senha e isolamento de tenant**, e com **buracos
graves em anonimato, superfície de ataque do SPA (já fechado),
autorização duplicada e capacidade do banco**.

A ordem correta não é "adicionar o que o Yespper tem". É:

1. Fechar P0 (bootstrap, anonimato real, autorização única).
2. Endurecer P1 (tokens, logout, índices, e-mail fora do request).
3. Só então melhorar usabilidade (inspirada no Leel: confiança do
   respondente, mobile, progresso sem expor quem) e aplicações
   futuras.

Qualquer feature nova antes disso aumenta a superfície e adia o
dia em que o produto pode, com honestidade, dizer que a pesquisa de
clima é anônima.
