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

- **E-mail:** SendGrid (API HTTPS) → Mailtrap → SMTP → outbox local.
  No **Render free**, SMTP (Gmail porta 587) é bloqueado (`Network is unreachable`).
  Use SendGrid para demo real.
- **R2:** vars `R2_*` no `.env` / Render (`sync: false`). Sem R2, o backend usa
  fallback local.

### Ativar e-mail real no Render (SendGrid)

1. Crie conta em [sendgrid.com](https://sendgrid.com).
2. Para produção, prefira **Domain Authentication** e publique no DNS os
   registros SPF/DKIM indicados pelo SendGrid. `Single Sender Verification`
   com Gmail serve para teste, mas tende a cair no spam.
3. Crie uma **API Key** com permissão de Mail Send.
4. No Render → `orizon-api` → **Environment**:
   - `SENDGRID_API_KEY` — a chave
   - `SENDGRID_FROM_EMAIL` — o **mesmo** Gmail verificado
   - `SENDGRID_FROM_NAME` — `Horizon`
   - `APP_PUBLIC_URL` — `https://orizon-api.onrender.com/app`
5. Opcional: mantenha `MAILTRAP_API_TOKEN` + `MAILTRAP_FROM_EMAIL` configurados
   como fallback. Ele só é usado quando o SendGrid rejeita a requisição.
6. Salve e aguarde o redeploy.
7. Confira `https://orizon-api.onrender.com/health/email` →
   `{"modo":"sendgrid"}`.

**Importante:** não cole a API Key no chat nem no git. Se o envio falhar, o painel
do TI mostra o motivo e o link de primeiro acesso. O estado `ACEITO` significa
que o provedor colocou a mensagem na fila; entrega no Gmail deve ser confirmada
em **Activity/Suppressions** no SendGrid.

## Testes

```powershell
pytest
```

## Arquitetura

- **Backend** decide autenticação, autorização, regras de negócio, convites,
  tokens, isolamento (IDOR = 404), auditoria.
- **React** só apresenta telas e chama a API.

## Auditoria e backlog

Análise crítica (segurança, anonimato do clima, carga do banco, usabilidade
vs Yespper/Leel, acesso TI de teste e roadmap): ver
[`docs/AUDITORIA_2026-09.md`](docs/AUDITORIA_2026-09.md).
