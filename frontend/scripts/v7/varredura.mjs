/**
 * Busca do CI do front v7. Não acessa a rede.
 * Uso: node scripts/v7/varredura.mjs [--raiz pasta-ou-arquivo]
 * Sem --raiz, varre frontend/src/v7.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const DOMINIOS_EMAIL = [
  "orgao.exemplo.gov.br",
  "consultoria.exemplo.gov.br",
  "saude.rioclaro.exemplo.gov.br",
  "valeazul.exemplo.gov.br",
  "horizon.exemplo.gov.br",
];

const URLS_OK = ["http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink"];

const EXTENSOES = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css", ".html", ".svg"]);

const REGRAS_SIMPLES = [
  [/\bfetch\s*\(/g, "fetch"],
  [/\baxios\b/g, "axios"],
  [/localStorage\.setItem/g, "localStorage"],
  [/\beval\s*\(/g, "eval"],
  [/\bnew\s+Function\b/g, "new-function"],
  [/dangerouslySetInnerHTML/g, "html-inseguro"],
  [/navigator\.serviceWorker/g, "service-worker"],
  [/\bPushManager\b/g, "push"],
  [/manifest\.webmanifest|rel\s*=\s*["']manifest["']/g, "pwa"],
  [/console\.log\s*\([\s\S]{0,180}?acao\s*\(/g, "console-acao"],
  [/\bXMLHttpRequest\b/g, "xhr"],
  [/\bWebSocket\b/g, "websocket"],
  [/\bEventSource\b/g, "event-source"],
  [/\bsendBeacon\s*\(/g, "send-beacon"],
  [/\bapi\s*\(/g, "api"],
];

const REGRAS_LOGICA = [
  [/\.reduce\s*\(/g, "logica-reduce"],
  [/\bMath\./g, "logica-math"],
  [/(?:<=|>=|<|>)\s*5\b/g, "logica-piso"],
  [/perfil\s*===/g, "logica-perfil"],
  [/\brole\s*===/g, "logica-role"],
];

const REGRAS_COR = [
  [/#[0-9a-fA-F]{3,8}\b/g, "cor-hex"],
  [/\brgba?\s*\(/g, "cor-rgb"],
  [/px\b/g, "cor-px"],
  [/cubic-bezier/g, "cor-curva"],
];

function linhaDo(texto, indice) {
  return texto.slice(0, indice).split("\n").length;
}

function listar(alvo) {
  const info = statSync(alvo);
  if (info.isFile()) return [alvo];
  const saida = [];
  const visitar = (dir) => {
    for (const nome of readdirSync(dir)) {
      if (nome === "node_modules" || nome === "dist") continue;
      const caminho = path.join(dir, nome);
      const stat = statSync(caminho);
      if (stat.isDirectory()) visitar(caminho);
      else if (EXTENSOES.has(path.extname(nome))) saida.push(caminho);
    }
  };
  visitar(alvo);
  return saida;
}

function especificadorProibido(spec) {
  const partes = spec.split(/[/\\]/);
  return partes.some((parte) => parte === "auth" || parte === "services" || parte === "api" || parte === "api.ts");
}

function registrar(achados, vistos, arquivo, texto, indice, regra, trecho) {
  const linha = linhaDo(texto, indice);
  const chave = `${arquivo}:${linha}:${regra}`;
  if (vistos.has(chave)) return;
  vistos.add(chave);
  achados.push({ arquivo, linha, regra, trecho: trecho.slice(0, 80) });
}

function aplicar(achados, vistos, arquivo, texto, regras) {
  for (const [re, regra] of regras) {
    re.lastIndex = 0;
    for (const match of texto.matchAll(re)) {
      registrar(achados, vistos, arquivo, texto, match.index ?? 0, regra, match[0]);
    }
  }
}

function logoPermitida(rel) {
  const partes = rel.split("/");
  if (partes.at(-1) === "index.html") return true;
  return partes.includes("ui") && /^Logo/i.test(partes.at(-1) ?? "");
}

/**
 * @param {string} raizArquivoOuPasta
 * @returns {{ ok: boolean, achados: { arquivo: string, linha: number, regra: string, trecho: string }[] }}
 */
export function varrer(raizArquivoOuPasta) {
  const raiz = path.resolve(raizArquivoOuPasta);
  const achados = [];
  const vistos = new Set();

  for (const arquivo of listar(raiz)) {
    const rel = path.relative(raiz, arquivo).replaceAll("\\", "/") || path.basename(arquivo);
    const texto = readFileSync(arquivo, "utf8");
    const partes = rel.split("/");
    const emTokens = partes.includes("tokens");
    const emUi = partes.includes("ui");
    const ehMascara = rel.endsWith("mascaras.ts");
    const ehFonte = rel.endsWith("fonteFicticia.ts");

    aplicar(achados, vistos, rel, texto, REGRAS_SIMPLES);
    if (!ehMascara) aplicar(achados, vistos, rel, texto, REGRAS_LOGICA);
    if (!emTokens) aplicar(achados, vistos, rel, texto, REGRAS_COR);

    const reUrl = /https?:\/\/[^\s"'`)<>]+/g;
    for (const match of texto.matchAll(reUrl)) {
      const url = match[0].replace(/[.,;]+$/, "");
      if (URLS_OK.some((ok) => url === ok || url.startsWith(`${ok}#`) || url.startsWith(`${ok}?`))) continue;
      registrar(achados, vistos, rel, texto, match.index ?? 0, "url", url);
    }

    const reEmail = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]*\.[A-Za-z0-9.-]*/g;
    for (const match of texto.matchAll(reEmail)) {
      if (match[0].includes("...") || match[0].includes("…")) continue;
      const host = match[0].split("@")[1].replace(/[),.;]+$/, "").toLowerCase();
      if (!host.includes(".") || DOMINIOS_EMAIL.includes(host)) continue;
      registrar(achados, vistos, rel, texto, match.index ?? 0, "email", match[0]);
    }

    const reImport = /\b(?:from|import)\s*(?:\(\s*)?["']([^"']+)["']/g;
    for (const match of texto.matchAll(reImport)) {
      const spec = match[1];
      if (spec.startsWith(".")) {
        const destino = path.resolve(path.dirname(arquivo), spec);
        const relativo = path.relative(raiz, destino);
        if (relativo.startsWith("..") || path.isAbsolute(relativo)) {
          registrar(achados, vistos, rel, texto, match.index ?? 0, "import-fora", spec);
        }
      } else if (especificadorProibido(spec)) {
        registrar(achados, vistos, rel, texto, match.index ?? 0, "import-fora", spec);
      }
    }

    if (!logoPermitida(rel)) {
      const reLogo = /horizon-logo\.png|assets\/logo\/horizon-logo/g;
      for (const match of texto.matchAll(reLogo)) {
        registrar(achados, vistos, rel, texto, match.index ?? 0, "logo", match[0]);
      }
    }

    if (!ehFonte && /\bfonteFicticia\b/.test(texto)) {
      const indice = texto.search(/\bfonteFicticia\b/);
      registrar(achados, vistos, rel, texto, indice, "fonte-ficticia", "fonteFicticia");
    }

    if (texto.includes("111.111.111-11") && /inválido|invalido/i.test(texto)) {
      registrar(achados, vistos, rel, texto, texto.indexOf("111.111.111-11"), "cpf-invalido", "111.111.111-11");
    }

    if (!emTokens && !emUi) {
      const reControle = /<(button|input|textarea|select)\b[^>]*?(?:style|className)\s*=/gi;
      for (const match of texto.matchAll(reControle)) {
        registrar(achados, vistos, rel, texto, match.index ?? 0, "componente", match[0].slice(0, 60));
      }
    }
  }

  return { ok: achados.length === 0, achados };
}

function main() {
  const indice = process.argv.indexOf("--raiz");
  const raiz =
    indice >= 0
      ? path.resolve(process.argv[indice + 1] ?? "")
      : fileURLToPath(new URL("../../src/v7", import.meta.url));
  const resultado = varrer(raiz);
  if (resultado.ok) {
    console.log("varredura ok");
    return 0;
  }
  console.error(`varredura reprovou (${resultado.achados.length}):`);
  for (const achado of resultado.achados) {
    console.error(`${achado.arquivo}:${achado.linha} [${achado.regra}] ${achado.trecho}`);
  }
  return 1;
}

const chamadoDireto = process.argv[1]?.replaceAll("\\", "/").endsWith("scripts/v7/varredura.mjs");
if (chamadoDireto) process.exit(main());
