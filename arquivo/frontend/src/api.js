const CHAVE_ACESSO = "horizon_access";
const CHAVE_REFRESH = "horizon_refresh";
const CHAVE_PAINEL = "horizon_painel";

const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export function urlApi(caminho) {
  if (!API || caminho.startsWith("http")) return caminho;
  return `${API}${caminho}`;
}

export function guardarSessao(dados) {
  sessionStorage.setItem(CHAVE_ACESSO, dados.access_token);
  sessionStorage.setItem(CHAVE_REFRESH, dados.refresh_token || "");
  sessionStorage.setItem(CHAVE_PAINEL, dados.painel || "");
}

export function limparSessao() {
  sessionStorage.removeItem(CHAVE_ACESSO);
  sessionStorage.removeItem(CHAVE_REFRESH);
  sessionStorage.removeItem(CHAVE_PAINEL);
}

export function tokenAtual() {
  return sessionStorage.getItem(CHAVE_ACESSO) || "";
}

export function painelAtual() {
  return sessionStorage.getItem(CHAVE_PAINEL) || "";
}

export async function sair() {
  const refresh = sessionStorage.getItem(CHAVE_REFRESH) || "";
  if (refresh) {
    await fetch(urlApi("/auth/sair"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    }).catch(() => {});
  }
  limparSessao();
}

function textoErro(corpo) {
  const detalhe = corpo.detail;
  if (Array.isArray(detalhe)) return "Confira os campos.";
  return detalhe || "Não foi possível concluir.";
}

export async function api(caminho, opcoes = {}) {
  const headers = { ...(opcoes.headers || {}) };
  let body = opcoes.body;
  if (opcoes.json) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opcoes.json);
  }
  const acesso = tokenAtual();
  if (acesso) headers.Authorization = `Bearer ${acesso}`;
  const resposta = await fetch(urlApi(caminho), { ...opcoes, headers, body });
  if (resposta.status === 204) return null;
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(textoErro(corpo));
  return corpo;
}
