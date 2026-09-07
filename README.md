# Horizon

Plataforma da consultora para aplicar pesquisas por cliente. Não é um clone do Yespper: nesta etapa não há OKR, feedback nem feed.

## Quem usa

- **Consultora** cria a pesquisa e conduz o projeto do cliente.
- **Funcionário** responde pelo link e vê a própria nota.
- **Órgão** consulta o resultado daquela pesquisa.

Cada cliente fica isolado. Conhecer o ID de uma pesquisa de outro órgão não dá acesso.

## Estado atual — Fase 1

Tudo no backend, sem tela. A consultora entra pela API, convida por e-mail (o destinatário define a própria senha) e quem esqueceu a senha recebe um token só no e-mail de acesso.

Três senhas erradas no mesmo e-mail gravam um bloqueio de 5 minutos na tabela `controle_acesso`. A senha nunca vai no e-mail e nunca volta na resposta.

## Como rodar

Requer Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# edite .env e cole a DATABASE_URL do Neon (não commite o .env)
uvicorn app.main:app --reload
```

Tela da consultora: `http://127.0.0.1:8000/app`

Para o e-mail sair da caixa local, preencha no `.env` (não cole no chat): `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` e `SMTP_FROM`.

- `GET http://127.0.0.1:8000/health` — a API está no ar (não usa banco).
- `GET http://127.0.0.1:8000/health/db` — o Neon responde `SELECT 1`. Sem URL, ou se a conexão falhar, retorna 503. Não altera schema.

Testes:

```powershell
pytest
```

Coloque `JWT_SECRET` no `.env`. Sem SMTP, o token do e-mail em development fica em `data/outbox/ultimo.txt`.

Endpoints (não há tela):

- `POST /auth/bootstrap` — primeira consultora, só se não existir usuário.
- `POST /auth/login` — e-mail e senha. A resposta traz `painel` (consultora, dev, orgao ou funcionario). CPF e CNPJ não entram no login.
- `POST /auth/convites` — uma conta de dev. O órgão entra pelo projeto. Cada funcionário do projeto tem conta e entra pelo mesmo login. O link da pesquisa continua sem nome.
- `POST /auth/primeiro-acesso` — destinatário define a senha.
- `POST /auth/recuperar-senha` — token vai só para o e-mail de acesso.
- `POST /auth/redefinir-senha` — grava a senha nova.
- `GET /projetos/rotulos` — rótulos da aba (já vêm do banco).
- `GET /projetos` — lista só os projetos da pessoa logada.
- `POST /projetos` — cria com CNPJ, rótulo, edital ou documento e e-mail do órgão.
- `POST /projetos/{id}/setores` — área do órgão. Só a consultora cria.
- `GET/PATCH /projetos/{id}/configuracao` — liga pesquisas. A IA fica DESATIVADA.
- `POST /projetos/{id}/reenviar-convite` — novo token se o órgão ainda não aceitou.
- `POST /biblioteca` — envia arquivo. Sem audiência, nasce PRIVADO, só para a consultora.
- `POST /projetos/{id}/pesquisas` — a consultora cria. O funcionário responde pelo token.
- `POST /pesquisas/{id}/encerrar` — fecha o link. O painel do órgão continua.
- `POST /pesquisas/{id}/modelo` — guarda o questionário para reutilizar no próximo projeto.
- Clima não devolve nota nem nome. Desempenho devolve a nota só para quem tem o token. O órgão vê a média.
- `GET /notificacoes` — avisos da própria conta. E-mail sai agora. Telefone fica gravado, sem SMS.

O log de acesso grava método, caminho e status. O token de resposta não entra no log. Backup e restore ficam no snapshot do Neon, não numa rota da API.

Quando o `.env` real existir, aplique só a migration de identidade. Ela não apaga tabela existente:

```powershell
alembic upgrade head
```

A `0001` não muda nada. A `0002` cria o que faltar e, se `usuarios` já existir, só acrescenta as colunas de bloqueio. Nunca use `Base.metadata.create_all`.

## Engine, session e pool

Três peças do SQLAlchemy, em ordem:

- **Engine** é a fábrica de conexões com o Postgres. Ela não guarda uma “tela” de dados; ela sabe como abrir e devolver conexões.
- **Session** é a conversa de um pedido: abre, lê ou grava, e fecha. No Horizon, uma session por request, descartada no fim, para um usuário não ver o rastro do outro.
- **Pool** é a fila de conexões já abertas, para não pagar o custo de conectar a cada request.

O Neon (e o pooler dele) limita quantas conexões um projeto pode ter ao mesmo tempo. Se cada processo da API guardar um pool grande, a cota acaba e o restante das requisições falha. Por isso o pool aqui é pequeno (`pool_size=5`, `max_overflow=0`) e usa `pool_pre_ping`: antes de reutilizar uma conexão, o SQLAlchemy pergunta se ela ainda está viva — o compute do Neon pode ter dormido.

## Fora desta fase

Tela, organização/projeto, biblioteca, pesquisa e R2. Sem OKR nem feedback.
