import assert from "node:assert/strict";
import { ApiErro, falhaPassageira, sessaoEncerrada } from "./sessaoEstado.ts";

const rede = new ApiErro(0, "Sem conexão com o servidor.", true);
const servidor = new ApiErro(500, "Não foi possível concluir.", false);
const acesso = new ApiErro(401, "Sessão inválida.", false);

assert.equal(sessaoEncerrada(acesso), true);
assert.equal(sessaoEncerrada(servidor), false);
assert.equal(sessaoEncerrada(rede), false);
assert.equal(acesso.rede, false);
assert.equal(rede.rede, true);
assert.equal(falhaPassageira(servidor), true);
assert.equal(falhaPassageira(rede), true);
assert.equal(falhaPassageira(acesso), false);
assert.equal(falhaPassageira(new ApiErro(403, "negado", false)), false);
assert.equal(acesso.message, "Sessão inválida.");
