const API = "";

function guardarSessao(dados) {
  sessionStorage.setItem("horizon_access", dados.access_token);
  sessionStorage.setItem("horizon_painel", dados.painel);
}

function tokenAtual() {
  return sessionStorage.getItem("horizon_access") || "";
}

async function api(caminho, opcoes = {}) {
  const { publico = false, json, headers: extras, ...resto } = opcoes;
  const headers = { ...(extras || {}) };
  if (json) {
    headers["Content-Type"] = "application/json";
    resto.body = JSON.stringify(json);
  }
  const acesso = tokenAtual();
  if (acesso && !publico) {
    headers.Authorization = `Bearer ${acesso}`;
  }
  const resposta = await fetch(`${API}${caminho}`, { ...resto, headers });
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

const DESTINO = {
  consultora: "painel.html",
  dev: "dev.html",
  orgao: "orgao.html",
  funcionario: "funcionario.html",
};

function irParaPainel(painel) {
  window.location.href = DESTINO[painel] || "entrar.html";
}

function sair() {
  sessionStorage.removeItem("horizon_access");
  sessionStorage.removeItem("horizon_painel");
  window.location.href = "entrar.html";
}

async function apiArquivo(caminho, formData) {
  const headers = {};
  const acesso = tokenAtual();
  if (acesso) {
    headers.Authorization = `Bearer ${acesso}`;
  }
  const resposta = await fetch(`${API}${caminho}`, {
    method: "POST",
    headers,
    body: formData,
  });
  const corpo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const detalhe = corpo.detail;
    const texto = Array.isArray(detalhe)
      ? "Confira o arquivo enviado."
      : detalhe || "Não foi possível enviar o arquivo.";
    throw new Error(texto);
  }
  return corpo;
}

async function baixarArquivo(documentoId, nome) {
  const headers = {};
  const acesso = tokenAtual();
  if (acesso) {
    headers.Authorization = `Bearer ${acesso}`;
  }
  const resposta = await fetch(`${API}/biblioteca/${documentoId}/arquivo`, {
    headers,
  });
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new Error(corpo.detail || "Download negado.");
  }
  const blob = await resposta.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome || "arquivo";
  link.click();
  URL.revokeObjectURL(url);
}
