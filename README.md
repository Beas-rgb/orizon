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

**Frontend oficial único:** React 19 + Vite + TypeScript + Tailwind 4 em
`frontend/`. Build em `web/app/`, servido em **`/app`** (SPA com
`basename="/app"`). Não há frontend HTML legado nem `/app/v2`.

Rotas oficiais (exemplos):
- `/app/` — landing
- `/app/entrar` — login (abre painel conforme o papel)
- `/app/cadastro`, `/app/recuperar`, `/app/primeiro-acesso`
- `/app/responder/:token` — resposta anônima de pesquisa
- `/app/inicio` — painel (consultora / órgão / funcionário / TI)
- `/app/projetos`, `/app/projetos/novo`, `/app/projetos/:id`

A pasta React antiga em `arquivo/frontend/` é só histórico e não é usada.

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

Abra `http://127.0.0.1:8000/app/`.

Frontend em desenvolvimento (hot reload):

```powershell
cd frontend
npm install
npm run dev
```

Build de produção do React (copia para `web/app/` antes do deploy):

```powershell
cd frontend
npm run build
# copie dist/* para web/app/
```

Conta do TI (opcional): preencha `ADMIN_NOME`, `ADMIN_EMAIL` e `ADMIN_SENHA` no
`.env`. A senha fica só no ambiente; no banco entra o hash Argon2id.

## E-mail e storage

- **E-mail:** Mailtrap (preferido) → SMTP → outbox local. Em modo `local`, a API
  pode devolver `link_primeiro_acesso` para a consultora/TI testarem.
- **R2:** vars `R2_*` no `.env` / Render (`sync: false`). Sem R2, o backend usa
  fallback local.

### Ativar e-mail real no Render (checklist)

1. Crie conta em [mailtrap.io](https://mailtrap.io) → API Tokens (Email Sending).
2. No Render → `orizon-api` → **Environment**, preencha:
   - `MAILTRAP_API_TOKEN` — token do Mailtrap
   - `MAILTRAP_FROM_EMAIL` — remetente autorizado no Mailtrap
   - `MAILTRAP_FROM_NAME` — `Horizon`
   - `APP_PUBLIC_URL` — `https://orizon-api.onrender.com/app`
3. Salve e aguarde o redeploy.
4. Confira `https://orizon-api.onrender.com/health/email` → deve ser
   `{"modo":"mailtrap"}`.
5. No painel TI (`/app/inicio`) o cartão de e-mail deixa de mostrar o aviso
   amarelo de modo local.

Sem esses valores, o envio continua em `local` (sem caixa real).

## Testes

```powershell
pytest
```

## Arquitetura

- **Backend** decide autenticação, autorização, regras de negócio, convites,
  tokens, isolamento (IDOR = 404), auditoria.
- **React** só apresenta telas e chama a API.
