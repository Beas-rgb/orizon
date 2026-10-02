# Segurança da sessão

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
