const API = "";

function guardarSessao(dados) {
  sessionStorage.setItem("horizon_access", dados.access_token);
  sessionStorage.setItem("horizon_painel", dados.painel);
}

function tokenAtual() {
  return sessionStorage.getItem("horizon_access") || "";
}

async function api(caminho, opcoes = {}) {
  const headers = { ...(opcoes.headers || {}) };
  if (opcoes.json) {
    headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(opcoes.json);
  }
  const acesso = tokenAtual();
  if (acesso) {
    headers.Authorization = `Bearer ${acesso}`;
  }
  const resposta = await fetch(`${API}${caminho}`, { ...opcoes, headers });
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = corpo.detail;
    const texto = Array.isArray(detalhe)
      ? "Confira e-mail e senha."
      : detalhe || "Não foi possível concluir.";
    throw new Error(texto);
  }
  return corpo;
}

function tokenDoLink() {
  return decodeURIComponent(window.location.hash.replace(/^#/, "")).trim();
}
