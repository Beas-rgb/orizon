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

const ONBOARDING_TEXTO = {
  criado: "Projeto criado",
  convite_pendente: "Convite do órgão pendente",
  convite_enviado: "Convite enviado — aguardando aceite",
  orgao_aceitou: "Órgão entrou no trabalho",
  convite_expirado: "Convite expirado",
};

const MOTIVO_TEXTO = {
  sem_convite: "Ainda não há convite registrado.",
  aguardando_envio: "Convite ainda não saiu. Use reenviar.",
  limite_de_convites: "Limite temporário de convites. Aguarde e reenvie.",
  falha_de_envio: "O e-mail falhou ao sair. Reenvie o convite.",
  email_ja_e_funcionario: "Este e-mail já é de um funcionário.",
  email_ja_e_consultor: "Este e-mail já é de uma consultora.",
  email_ja_e_ti: "Este e-mail já é da conta de TI.",
  conta_inativa: "A conta deste e-mail está inativa.",
  email_ja_tem_acesso: "Este e-mail já tem outro tipo de acesso.",
  email_indisponivel: "Não foi possível usar este e-mail.",
};

function textoOnboarding(item) {
  const estado = item.onboarding_estado || "";
  const base = ONBOARDING_TEXTO[estado] || estado || "—";
  if (!item.convite_motivo) return base;
  const motivo = MOTIVO_TEXTO[item.convite_motivo] || item.convite_motivo;
  return base + " — " + motivo;
}

async function copiarTexto(texto) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(texto);
    return;
  }
  const campo = document.createElement("textarea");
  campo.value = texto;
  document.body.appendChild(campo);
  campo.select();
  document.execCommand("copy");
  campo.remove();
}

function mascaraCnpj(valor) {
  const d = String(valor || "")
    .toUpperCase()
    .replace(/[^0-9A-Z]/g, "")
    .slice(0, 14);
  return d
    .replace(/^(.{2})(.)/, "$1.$2")
    .replace(/^(.{2})\.(.{3})(.)/, "$1.$2.$3")
    .replace(/\.(.{3})(.)/, ".$1/$2")
    .replace(/(.{4})(.)/, "$1-$2");
}
