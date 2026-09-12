# Horizon

Plataforma da consultora para aplicar pesquisas por cliente. Não é um clone do
Yespper: nesta etapa não há OKR, feedback nem feed.

## Quem usa

- **TI (dev)** — primeira conta (`bootstrap` ou `ADMIN_*` no `.env`). Autoriza
  pedidos de consultora e vê diagnóstico.
- **Consultora** — pede conta; só nasce depois da autorização do TI. Cria
  projeto, pesquisa e convites.
- **Órgão** — entra pelo convite do projeto; vê o resultado daquele trabalho.
- **Funcionário** — entra pelo convite do projeto; responde pelo link da pesquisa
  e vê a própria nota (quando o tipo devolver).

Cada cliente fica isolado. Conhecer o ID de um projeto ou pesquisa de outro
órgão responde **404** (não confirma que o recurso existe).

## Estado atual

Backend das fases 0–5 e 7 concluído e coberto por testes. Fase 6 (IA) suspensa
(`ia_modo = DESATIVADA`).

**Frontend definitivo**: React 19 + Vite + TypeScript + Tailwind 4 em
`frontend/`. Build de produção em `web/app/`, servido em `/app/v2` (rota SPA
com fallback para `index.html`).

**Frontend legado (teste)**: HTML/JS puro em `web/`, servido em `/app`. Ainda
funcional para validação rápida, mas não recebe trabalho novo. A pasta React
antiga ficou em `arquivo/frontend/` e não recebe trabalho novo.

Fluxos cobertos no React:
- entrar / recuperar senha / primeiro acesso / cadastro da consultora
- painel da consultora (dashboard, trabalhos, criar projeto, detalhe com
  equipe, pesquisas, biblioteca)
- painel do órgão (trabalhos + resultado agregado)
- painel do funcionário (trabalhos + link de resposta)
- painel do TI (pedidos, consultores, diagnóstico, link de primeiro acesso)

Desenho Figma final e R2 em produção ficam para depois.

## Como rodar

Requer Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# edite .env: DATABASE_URL, JWT_SECRET (não commite o .env)
alembic upgrade head
uvicorn app.main:app --reload
```

Abra `http://127.0.0.1:8000/app`.

Conta do TI (opcional): preencha `ADMIN_NOME`, `ADMIN_EMAIL` e `ADMIN_SENHA` no
`.env`. A senha fica só no ambiente; no banco entra o hash Argon2id.

Para o e-mail sair de verdade, instale o SDK (`pip install mailtrap`) e
preencha no `.env` (não cole no chat): `MAILTRAP_API_TOKEN` e
`MAILTRAP_FROM_EMAIL`. O token sai em https://mailtrap.io/settings/api-tokens.
Os envios aparecem em https://mailtrap.io/sending/email_logs. Sem Mailtrap,
ainda vale SMTP (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`). Sem
os dois, o token do convite fica em `data/outbox/`.

- `GET /health` — API no ar (não usa banco).
- `GET /health/db` — Neon responde `SELECT 1`. Sem URL, ou se falhar: 503.

```powershell
pytest
```

## Senha e acesso

Regra de senha (todos os papéis), só no backend: mínimo 8 caracteres, uma
maiúscula, um número e um caractere especial. No banco só o hash.

Três senhas erradas no mesmo e-mail bloqueiam por 5 minutos. A senha nunca vai
no e-mail e nunca volta na resposta.

## Contas e convites

- `POST /auth/bootstrap` — **primeira conta TI**, só se a tabela de usuários
  estiver vazia.
- `POST /auth/cadastro-consultora` — pedido público (pendente até 5 dias).
- `GET/POST /dev/pedidos` e `GET /dev/consultores` — só o TI.
- `POST /auth/login` — e-mail e senha; a resposta traz `painel`.
- Órgão e funcionário entram pelo projeto. O órgão é **por projeto** (não uma
  vaga global no sistema).
- `POST /auth/primeiro-acesso` — destinatário define a senha.
- `POST /auth/recuperar-senha` / `POST /auth/redefinir-senha` — token só no
  e-mail de acesso.

## Projetos e pesquisas (API)

- `GET /projetos` — só os da pessoa logada.
- `POST /projetos` — CNPJ, rótulo, vínculo e e-mail do órgão (convite automático).
- `GET /projetos/{id}/equipe` — só a consultora dona; sem token na resposta.
- `GET/PATCH /projetos/{id}/configuracao` — liga pesquisas; IA continua
  DESATIVADA.
- Pesquisas: criar, perguntas, publicar, tokens, painel agregado, encerrar.
- Biblioteca: upload com visibilidade decidida no backend (PRIVADO por padrão).

O log de acesso grava método, caminho e status. Token de resposta não entra no
log. Backup e restore ficam no snapshot do Neon.

Nunca use `Base.metadata.create_all`. Só migrations Alembic.

## Engine, session e pool

- **Engine** — fábrica de conexões com o Postgres.
- **Session** — uma por request; fecha no fim.
- **Pool** — pequeno (`pool_size` baixo, `max_overflow=0`) por causa da cota do
  Neon; `pool_pre_ping` evita conexão morta após o compute dormir.

## Fora desta etapa

Desenho Figma final, tela de resposta da pesquisa, tela de biblioteca, R2 em
produção e IA. Sem OKR nem feedback.
