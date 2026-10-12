# Segurança da sessão

> Nota 08/10/2026: esta página descreve hash, fila, refresh e IP. Não marca isolamento nem CLIMA como corrigidos. A matriz com estado da evidência está em `docs/AUDITORIA_BANCO_SEGURANCA_2026-10.md`. A suíte não foi reexecutada no Passo 0.

## Hash da senha

Argon2id via `argon2-cffi`. O padrão continua o que já estava no banco: 65536 KiB de memória, 3 iterações, paralelismo 4. Esses números ficam na configuração. Se um hash antigo não usa os parâmetros atuais, o login certo grava um hash novo. Senha errada não reescreve nada.

## Fila do hash

No máximo 2 hashes ao mesmo tempo. A fila espera até 18. Quem não entra recebe 503 e o cabeçalho `Retry-After: 5`, com a mensagem "Sistema ocupado. Tente novamente em instantes." A conta que não existe passa pelo mesmo limite, para o tempo não revelar se o e-mail existe.

## Conexão do banco

A leitura do usuário termina antes do hash. A conexão volta ao pool. Depois do hash, uma transação nova confere de novo se a conta segue ativa.

## Refresh

O navegador renova o acesso com um único pedido compartilhado, cerca de 60 segundos antes de expirar, e também quando a aba volta e falta menos de 60 segundos. Um 401 tenta renovar uma vez. Se o refresh responde 401 ou 429, a sessão é limpa e não há nova tentativa até o próximo login.

## IP

`TRUSTED_PROXY_HOPS` começa em 0. Nesse valor, o cabeçalho enviado pelo navegador é ignorado. A conta TI vê `GET /dev/diagnostico/ip` para escolher o número no painel.

## Limites

Três senhas erradas no mesmo e-mail esperam 5 minutos. Trinta senhas erradas no mesmo IP, em e-mails diferentes, também esperam 5 minutos. Um login certo não zera o contador do IP.

## O que não entra em log

Senha, hash, token e URL do banco não são escritos em log nem na resposta de erro.

## Correções de 12/10/2026 (locais, com teste)

- `scripts/reset_manter_ti.py` recusa `APP_ENV=production`, host fora de `localhost`/`127.0.0.1`/`HORIZON_RESET_HOSTS` e falta de `HORIZON_RESET_CONFIRMA=APAGAR_DADOS_LOCAIS`. A recusa acontece antes de abrir conexão (`tests/test_reset_e_admin.py`).
- Convite não concede TI, nem quando não existe TI. A conta TI nasce de `ADMIN_*` no boot (`garantir_admin`) ou do bootstrap local.
- A importação não vincula conta existente de outro papel nem funcionário de trabalho de outra consultora. A linha aparece com erro na prévia; o caminho é o convite (`tests/test_importacao.py`).
- Em produção sem R2, upload e mídia falham em vez de gravar em disco efêmero, e `/health/ready` responde `armazenamento_ausente`. O boot ainda sobe sem R2: falta confirmar no painel do Render se as variáveis existem.
- Resultado da avaliação de desempenho: a média dos subordinados some para o avaliado e para o órgão quando menos de 5 pessoas responderam (`perspectivas_suprimidas`). A consultora continua vendo. A nota final ainda inclui o grupo; esconder também os pesos ou redistribuir é decisão pendente.
- `/auth/cadastro-consultora` usa o mesmo IP de cliente que as outras rotas.
- Biblioteca, setores e cargos têm teto de página.
- Timeouts por transação disponíveis em `DB_STATEMENT_TIMEOUT_MS` e `DB_LOCK_TIMEOUT_MS` (zero desliga). Testado no PostgreSQL local.
- O container roda como usuário `horizon` (uid 10001).

## Triagem de ferramentas (12/10/2026, máquina local)

- Bandit `-ll`: 4 médios, nenhum alto. `urlopen` em `cnpj.py` e `email.py` usa URL fixa `https`; o CNPJ entra só depois de `normalizar_cnpj`. `manutencao.py` monta SQL só com nomes de uma lista interna. Os quatro são falsos positivos.
- `pip-audit` no `.venv`: `urllib3` 2.7.0 (transitivo do `botocore`) com correção em 2.8.0. `python-jose` e `ecdsa` aparecem no `.venv` local, mas não estão no `pyproject.toml`. Fixar `urllib3` entra com o lockfile.
- `npm audit --omit=dev`: 0 vulnerabilidades. Com dev: 1 alta em `source-map-js`, só no build.
- Varredura de segredos no working tree e no histórico: as URLs do Neon encontradas são placeholders (`USER:PASSWORD@HOST`).
