/**
 * Lê tokens-final-2026-10-16.json e escreve tokens.css, tokens.ts e REGRAS.md.
 * Sem rede. A saída é determinística e as chaves saem em ordem alfabética.
 */
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PULAR = new Set(["diverge", "codigo_v7", "valor_codigo", "codigo_v7_hoje", "uso"]);
const CHAVES_CSS = new Set([
  "sans-serif", "serif", "monospace", "system-ui", "linear", "uppercase", "lowercase",
  "none", "auto", "normal", "bold", "italic", "block", "inline", "flex", "solid",
  "transparent", "inherit", "initial", "unset", "ease", "center", "antialiased",
  "tabular-nums", "transform", "opacity", "inset", "and", "or", "not", "in", "srgb",
  "var", "rgba", "rgb", "calc", "blur", "translatex", "translatey", "webkit-font-smoothing",
  "apple-system", "blinkmacsystemfont", "arial", "inter", "montserrat",
]);

function slug(texto) {
  const trocas = { ã: "a", á: "a", â: "a", à: "a", é: "e", ê: "e", í: "i", ó: "o", ô: "o", õ: "o", ú: "u", ç: "c" };
  let s = String(texto).toLowerCase();
  for (const [de, para] of Object.entries(trocas)) s = s.replaceAll(de, para);
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48);
}

function prefixar(valor) {
  return String(valor)
    .replace(/var\(--(?!hz-)/g, "var(--hz-")
    .replace(/(^|[^\w-])--(?!hz-)([a-zA-Z0-9-]+)/g, "$1--hz-$2");
}

function semUnidadePermitida(nome) {
  return nome.includes("-peso") || nome.includes("altura-linha") || nome.includes("-z-") || nome.includes("opacidade");
}

function temDescricao(valor) {
  let s = valor.replace(/"[^"]*"/g, " ");
  let anterior;
  do {
    anterior = s;
    s = s.replace(/\b[A-Za-z-]+\([^()]*\)/g, " ");
  } while (s !== anterior);
  s = s.replace(/#[0-9a-fA-F]{3,8}\b/g, " ");
  s = s.replace(/-?\d+(?:\.\d+)?(?:px|em|rem|ms|s|%|vh|vw|deg)?/gi, " ");
  const palavras = s.match(/[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]*/g) ?? [];
  return palavras.some((palavra) => !CHAVES_CSS.has(palavra.toLowerCase()));
}

export function tokensInvalidos(entradas) {
  const culpados = [];
  for (const { nome, valor } of entradas) {
    const motivos = [];
    if (String(nome).includes("ate-760px")) motivos.push("ate-760px");
    if (String(valor).startsWith("--") && !String(valor).includes("var(")) motivos.push("var");
    const abre = [...String(valor)].filter((c) => c === "(").length;
    const fecha = [...String(valor)].filter((c) => c === ")").length;
    if (abre !== fecha) motivos.push("parenteses");
    if (/\\;|@media|@supports|→|—|·/.test(String(valor))) motivos.push("proibido");
    if (/^\d+(?:\.\d+)?$/.test(String(valor).trim()) && !semUnidadePermitida(nome)) motivos.push("unidade");
    if (temDescricao(String(valor))) motivos.push("descricao");
    if (motivos.length) culpados.push({ nome, valor, motivos });
  }
  return culpados;
}

function valido(nome, valor) {
  return tokensInvalidos([{ nome, valor }]).length === 0;
}

function mapaBruto(json) {
  const mapa = new Map();
  const add = (nome, valor) => {
    if (valor == null || valor === "") return;
    const css = `--hz-${nome}`;
    if (mapa.has(css)) throw new Error(`token duplicado ${css}`);
    mapa.set(css, prefixar(valor).trim());
  };
  for (const cor of json.cores) add(cor.token.replace(/^--/, ""), cor.design);
  const visitar = (no, prefixo) => {
    if (no == null) return;
    if (typeof no === "string" || typeof no === "number" || typeof no === "boolean") {
      add(prefixo, no);
      return;
    }
    if (Array.isArray(no)) {
      no.forEach((item, indice) => {
        if (item && typeof item === "object" && typeof item.uso === "string") visitar(item, `${prefixo}-${slug(item.uso)}`);
        else visitar(item, `${prefixo}-${indice}`);
      });
      return;
    }
    for (const [chave, valor] of Object.entries(no)) {
      if (PULAR.has(chave)) continue;
      const nome = chave.startsWith("--") ? `var-${slug(chave)}` : slug(chave);
      visitar(valor, `${prefixo}-${nome}`);
    }
  };
  visitar(json.tipografia, "tipo");
  visitar(json.espacamentos, "espaco");
  visitar(json.raios, "raio");
  visitar(json.sombras, "sombra");
  visitar(json.breakpoints, "bp");
  visitar(json.z_index, "z");
  visitar(json.menu, "menu");
  visitar(json.curva, "curva");
  return mapa;
}

function normalizar(nome, valor) {
  let n = nome.replaceAll("-ate-760px", "");
  let v = valor;
  if (v === "--hz-font-brand") v = "var(--hz-tipo-familias-marca)";
  else if (/^--hz-[\w-]+$/.test(v)) v = `var(${v})`;
  else v = v.replace(/(?<!var\()--hz-[\w-]+/g, (token) => `var(${token})`);
  if (n.includes("escala-px-") && /^\d+(?:\.\d+)?$/.test(v)) v = `${v}px`;
  return { nome: n, valor: v };
}

function limpar(nome, valor) {
  const atual = normalizar(nome, valor);
  const regras = [];
  const celular = atual.valor.match(/^(.*)\s+\(celular\s+([^)]+)\)$/);
  if (celular && valido(atual.nome, celular[1].trim()) && valido(`${atual.nome}-celular`, celular[2].trim())) {
    return {
      saida: [
        { nome: atual.nome, valor: celular[1].trim() },
        { nome: `${atual.nome}-celular`, valor: celular[2].trim() },
      ],
      regras,
    };
  }
  const paren = atual.valor.match(/^(.*)\s+\(([^)]+)\)$/);
  if (paren && valido(atual.nome, paren[1].trim())) {
    regras.push({ nome: atual.nome, original: valor });
    return { saida: [{ nome: atual.nome, valor: paren[1].trim() }], regras };
  }
  if (valido(atual.nome, atual.valor)) {
    return { saida: [atual], regras };
  }
  const corte = atual.valor.split(/\s+[—–]\s+|\s+→\s+|,\s+(?=[A-Za-zÀ-ÿ])/)[0]?.trim();
  if (corte && corte !== atual.valor && valido(atual.nome, corte)) {
    regras.push({ nome: atual.nome, original: valor });
    return { saida: [{ nome: atual.nome, valor: corte }], regras };
  }
  regras.push({ nome: atual.nome, original: valor });
  return { saida: [], regras };
}

export function gerarDeJson(json) {
  const tokens = new Map();
  const regras = [];
  for (const [nome, valor] of mapaBruto(json)) {
    const limpo = limpar(nome, valor);
    for (const item of limpo.saida) {
      if (tokens.has(item.nome)) throw new Error(`token duplicado depois da limpeza ${item.nome}`);
      tokens.set(item.nome, item.valor);
    }
    regras.push(...limpo.regras);
  }
  const nomes = [...tokens.keys()].sort();
  const css = [
    "/* Gerado de tokens-final-2026-10-16.json (campo design). Não editar à mão. */",
    ":root {",
    ...nomes.map((nome) => `  ${nome}: ${tokens.get(nome)};`),
    "}",
    "@font-face {",
    "  font-family: \"Inter\";",
    "  src: url(\"../../assets/fonts/Inter.ttf\") format(\"truetype\");",
    "  font-weight: 100 900;",
    "  font-style: normal;",
    "  font-display: block;",
    "}",
    "@font-face {",
    "  font-family: \"Montserrat\";",
    "  src: url(\"../../assets/fonts/Montserrat.ttf\") format(\"truetype\");",
    "  font-weight: 100 900;",
    "  font-style: normal;",
    "  font-display: block;",
    "}",
    "",
  ].join("\n");
  const ts = [
    "/** Gerado de tokens-final-2026-10-16.json (campo design). Não editar à mão. */",
    "export const variaveisCss = {",
    ...nomes.map((nome) => `  ${JSON.stringify(nome)}: ${JSON.stringify(tokens.get(nome))},`),
    "} as const;",
    "",
  ].join("\n");
  const md = [
    "# Regras que não viraram token",
    "",
    "Gerado de tokens-final-2026-10-16.json. O texto original entra inteiro.",
    "",
    ...regras
      .sort((a, b) => a.nome.localeCompare(b.nome))
      .map((item) => `## ${item.nome}\n\n${item.original}\n`),
    "",
  ].join("\n");
  return { css, ts, regras: md, tokens };
}

function main() {
  const jsonPath = fileURLToPath(new URL("./tokens-final-2026-10-16.json", import.meta.url));
  const json = JSON.parse(readFileSync(jsonPath, "utf8"));
  const gerado = gerarDeJson(json);
  const dir = fileURLToPath(new URL("../../src/v7/tokens/", import.meta.url));
  writeFileSync(path.join(dir, "tokens.css"), gerado.css);
  writeFileSync(path.join(dir, "tokens.ts"), gerado.ts);
  writeFileSync(path.join(dir, "REGRAS.md"), gerado.regras);
  console.log(`tokens ${gerado.tokens.size}`);
}

if (process.argv[1]?.replaceAll("\\", "/").endsWith("scripts/v7/gerar-tokens.mjs")) main();
