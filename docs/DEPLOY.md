# Deploy

A tela pode sair do Cloudflare Pages. A API continua no Render Free. `web/app` e a rota `/app` da API ficam até a Fase 10.

## Páginas

No painel do Cloudflare Pages:

- Diretório do projeto: `frontend`
- Comando: `npm ci && npm run build:pages`
- Saída: `dist` (base `/`)
- `NODE_VERSION` = `22`
- `VITE_API_URL` = a URL da API, sem barra no fim, por exemplo `https://orizon-api.onrender.com`
- `VITE_BASE` = `/`

No Render, `APP_PUBLIC_URL` passa a ser a URL do Pages **sem** `/app`, por exemplo `https://<projeto>.pages.dev`. Assim o e-mail de primeiro acesso e o link de resposta não ganham `/app` duas vezes.

`CORS_ORIGINS` recebe a origem do Pages (`https://<projeto>.pages.dev`). `CORS_ORIGIN_REGEX` fica vazio, a menos que você precise de um padrão. Não grave domínio fixo no código.

## Variáveis

Os valores ficam no painel. Este arquivo não os repete.

- Render: `APP_ENV`, `DATABASE_URL`, `JWT_SECRET`, `APP_PUBLIC_URL`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`, chaves de e-mail, R2, conta de desenvolvimento.
- Pages: `VITE_API_URL`, `VITE_BASE`, `NODE_VERSION`.

## Virada

1. Publicar o Pages e abrir a URL. A entrada tem de aparecer mesmo com a API dormindo.
2. Conferir o login depois do aviso de acordar.
3. No Render, apontar `APP_PUBLIC_URL` e `CORS_ORIGINS` para o Pages.
4. Enviar um primeiro acesso de teste e ver se o link abre no Pages, sem `/app` duplicado.
5. A URL antiga `https://orizon-api.onrender.com/app` continua servindo a tela que está em `web/app`.
   Para republicar esse fallback localmente: `cd frontend && npm run publish:app`.

## Painéis

- Render: https://dashboard.render.com
- Neon: https://console.neon.tech
- Cloudflare Pages: https://dash.cloudflare.com

## Regiões (Fase 0)

| Serviço | Região | Anotado em |
|---|---|---|
| Neon (Postgres) | `aws-sa-east-1` (São Paulo) | 02/10/2026 via API Neon |
| Render (API) | _conferir no painel_ (header `/health` não expõe a região) | |
| Neon branch staging | `staging` (filho de `production`) | 02/10/2026 |

Pages: `https://orizon-a0u.pages.dev` (projeto Cloudflare `orizon`).
Env do Pages: `VITE_API_URL`, `VITE_BASE=/`, `NODE_VERSION=22`.
Preview: `https://preview.orizon-a0u.pages.dev`.

No Render, para virar a rota principal do front (ainda manual — sem API Render aqui):
1. `APP_PUBLIC_URL=https://orizon-a0u.pages.dev`
2. `CORS_ORIGINS=https://orizon-a0u.pages.dev`

`TRUSTED_PROXY_HOPS` fica em 0 até a medição. Com 0, o cabeçalho `X-Forwarded-For` é ignorado. A conta TI chama `GET /dev/diagnostico/ip`, compara `ip` com o IP público e só então grava o número no Render.
