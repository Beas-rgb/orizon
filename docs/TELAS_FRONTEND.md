# Telas 01–93 — matriz e decisões

Referência visual: índice do ZIP atualizado. Telas 01–30 e 54 não vieram em SVG; a interface atual serve. Peso morto **não foi apagado**.

## Decisão de hospedagem

O frontend oficial continua embutido em `/app` no Render (caminho reversível). Cloudflare Pages continua opcional (`CORS_ORIGINS` + `APP_PUBLIC_URL` sem `/app`). Não migrar agora: o SPA já publica em `web/app`.

## Menu do trabalho (proposta; confirmação do João)

Avaliações e Modelos ficam no menu da consultora, fora do trabalho. Dentro do trabalho: Visão, Estrutura, Participantes, Pesquisas, Resultados, Histórico, Biblioteca, Configurações, Entregas.

## Matriz (ação)

| Nº | Tela | Rota / componente | Ação |
|---|---|---|---|
| 01–15, 18–47 | já no produto | `Paineis`, `ProjetosPages`, `PesquisaEditorPage`, `AuthPages`, `LabPage` | ajustar estados |
| 16 | Salvar como modelo | editor, diálogo | ligar `POST /pesquisas/{id}/modelo` |
| 17 | Criar de modelo | trabalho, diálogo | ligar `POST .../pesquisas/de-modelo` |
| 49–53 | estados | `src/ui/EstadosTela.tsx` | usar em todas as páginas novas |
| 55 | Biblioteca principal | `/biblioteca` | listar API existente |
| 56–57 | Documentos órgão/servidor | `/documentos` | mesma API, visibilidade no servidor |
| 58 | Banco de perguntas | `/banco-perguntas` | `GET /modelos` |
| 60 | Editar pessoa | diálogo no trabalho | `PUT /projetos/{id}/perfis` |
| 62, 70 | Notificações | `/notificacoes` | API existente |
| 65 | Minhas notas | `/minhas-notas` | `GET /eu/pesquisas/{id}/nota` |
| 66 | Entregas | `?aba=entregas` | `GET /projetos/{id}/entregas` |
| 67 | Editar trabalho | diálogo | `PATCH /projetos/{id}` |
| 68 | Encerrar pesquisa | diálogo no editor | `POST /pesquisas/{id}/encerrar` |
| 69 | Trocar senha logado | `/conta` | `POST /auth/senha` |
| 71–75, 78 | Organização | `/organizacao` e aba do trabalho | árvore existente; 75/78 dependem de pesos/K (Fase 2: faixa, não pesos) |
| 76–77 | Trabalho início / dashboard | `/projetos/:id` e `GET /projetos/{id}/resumo` | K no servidor |
| 79–93 | carregamento | `EstadosTela` | 4 estados + envio/timeout/offline |
| — | 404 real | `*` | `Pagina404` |

## Peso morto (só inventário)

`Navbar`, `Sidebar`, `JobHistory`, `MetricsPanel`, `SmartBriefing`, `QuickAccess` não são importados por rota. `clsx`. `sessaoEstado.test.ts` fora do include do Vitest. `arquivo/frontend/` só na documentação. Remoção exige diff aprovado.
