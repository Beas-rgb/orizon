# Frontend React do Horizon

Build de produção:

```bash
npm run build
```

O resultado fica em `dist/`. Para servir com a API FastAPI:

1. Copie `dist/*` para `web/app/` (ou configure o StaticFiles)
2. Ou use um serviço separado (Cloudflare Pages, Vercel, Netlify)

## Desenvolvimento

```bash
npm install
npm run dev
```

Abre em `http://127.0.0.1:5173` com proxy para a API local (`:8000`).

## Variáveis

- `VITE_API_URL` — URL da API em produção (ex.: `https://orizon-api.onrender.com`)
