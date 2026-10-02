import { ApiErro } from "./sessaoEstado";
import { guardarSessao, limparSessao, urlApi } from "./api";

const CHAVE_REFRESH = "horizon_refresh";
const AVISO = "horizon_aviso";

let emVoo: Promise<void> | null = null;
let bloqueado = false;

export function liberarRefresh() {
  bloqueado = false;
}

export function expiraEmMs(token: string): number | null {
  try {
    const parte = token.split(".")[1];
    if (!parte) return null;
    const json = JSON.parse(atob(parte.replace(/-/g, "+").replace(/_/g, "/"))) as {
      exp?: number;
    };
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

async function executar() {
  const refresh = sessionStorage.getItem(CHAVE_REFRESH) || "";
  if (!refresh || bloqueado) {
    bloqueado = true;
    limparSessao();
    window.dispatchEvent(new Event("horizon:sessao-expirada"));
    throw new ApiErro(401, "Sessão inválida.", false);
  }
  let resposta: Response;
  try {
    resposta = await fetch(urlApi("/auth/refresh"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
  } catch {
    throw new ApiErro(0, "Sem conexão com o servidor.", true);
  }
  if (resposta.status === 401 || resposta.status === 429) {
    bloqueado = true;
    limparSessao();
    window.dispatchEvent(new Event("horizon:sessao-expirada"));
    throw new ApiErro(resposta.status, "Sessão inválida.", false);
  }
  if (!resposta.ok) {
    throw new ApiErro(resposta.status, "Não foi possível concluir.", false);
  }
  const dados = (await resposta.json()) as {
    access_token: string;
    refresh_token?: string;
    painel?: string;
    usuario?: { id: string; nome: string; email: string; painel: "consultora" | "orgao" | "funcionario" | "dev" | "" };
  };
  guardarSessao(dados);
  window.dispatchEvent(new CustomEvent("horizon:sessao-renovada", { detail: dados.usuario }));
}

export function renovarSessao() {
  if (bloqueado) {
    throw new ApiErro(401, "Sessão inválida.", false);
  }
  if (!emVoo) {
    emVoo = executar().finally(() => {
      emVoo = null;
    });
  }
  return emVoo;
}

export function avisoSessaoExpirada() {
  sessionStorage.setItem(AVISO, "Sua sessão expirou. Entre novamente.");
}

export function lerAvisoSessao() {
  const texto = sessionStorage.getItem(AVISO) || "";
  sessionStorage.removeItem(AVISO);
  return texto;
}
