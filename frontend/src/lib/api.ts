const CHAVE_ACESSO = "horizon_access";
const CHAVE_REFRESH = "horizon_refresh";
const CHAVE_PAINEL = "horizon_painel";

const API = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export type Painel = "consultora" | "orgao" | "funcionario" | "dev" | "";

export function urlApi(caminho: string) {
  if (!API || caminho.startsWith("http")) return caminho;
  return `${API}${caminho}`;
}

export function guardarSessao(dados: {
  access_token: string;
  refresh_token?: string;
  painel?: string;
}) {
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

export function painelAtual(): Painel {
  return (sessionStorage.getItem(CHAVE_PAINEL) || "") as Painel;
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

function textoErro(corpo: { detail?: unknown }) {
  const detalhe = corpo.detail;
  if (Array.isArray(detalhe)) {
    const msgs = detalhe
      .map((item) => {
        if (!item || typeof item !== "object") return "";
        const erro = item as { loc?: unknown[]; msg?: string };
        const campo = Array.isArray(erro.loc)
          ? String(erro.loc[erro.loc.length - 1] || "")
          : "";
        const msg = erro.msg || "";
        if (campo && msg) return `${campo}: ${msg}`;
        return msg;
      })
      .filter(Boolean);
    return msgs[0] || "Confira os campos.";
  }
  if (typeof detalhe === "string") return detalhe;
  return "Não foi possível concluir.";
}

type ApiOpcoes = RequestInit & { json?: unknown };

export async function api<T = unknown>(caminho: string, opcoes: ApiOpcoes = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(opcoes.headers as Record<string, string> | undefined),
  };
  let body = opcoes.body;
  if (opcoes.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opcoes.json);
  }
  const acesso = tokenAtual();
  if (acesso) headers.Authorization = `Bearer ${acesso}`;

  const { json: _json, ...rest } = opcoes;
  const resposta = await fetch(urlApi(caminho), { ...rest, headers, body });
  if (resposta.status === 204) return null as T;
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(textoErro(corpo));
  return corpo as T;
}
