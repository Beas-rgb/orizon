import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

export const HASH_FAVICON = "0baefe82f6571f15336346652d6f375369b8e01a7b2b022cc03e888e24a25845";

function ignorar(rel: string) {
  const partes = rel.split("/");
  return partes.includes("node_modules") || partes.includes("dist") || rel.includes("tests/v7/fixtures/");
}

export function listarSvg(raiz: string) {
  const saida: string[] = [];
  const visitar = (dir: string) => {
    for (const nome of readdirSync(dir)) {
      const caminho = path.join(dir, nome);
      const rel = path.relative(raiz, caminho).replaceAll("\\", "/");
      if (ignorar(rel)) continue;
      const info = statSync(caminho);
      if (info.isDirectory()) visitar(caminho);
      else if (nome.endsWith(".svg")) saida.push(rel);
    }
  };
  visitar(raiz);
  return saida.sort();
}

export function problemasSvg(texto: string) {
  const t = texto.toLowerCase();
  const erros: string[] = [];
  if (t.includes("<script")) erros.push("script");
  if (t.includes("<foreignobject")) erros.push("foreignObject");
  if (/\son[a-z]+=/.test(t)) erros.push("evento");
  for (const match of t.matchAll(/(?:xlink:)?href\s*=\s*["']([^"']*)["']/g)) {
    if (!match[1].startsWith("#")) erros.push("href");
  }
  for (const match of t.matchAll(/url\(\s*["']?([^)"']+)/g)) {
    if (!match[1].trim().startsWith("#")) erros.push("url");
  }
  if (t.includes("@import")) erros.push("import");
  if (t.includes("javascript:")) erros.push("javascript");
  if (t.includes("<!entity")) erros.push("entity");
  if (t.includes("<!doctype")) erros.push("doctype");
  return erros;
}

export function svgForaDaAllowlist(arquivos: string[], raiz: string) {
  const erros: string[] = [];
  for (const rel of arquivos) {
    if (rel !== "public/favicon.svg") {
      erros.push(rel);
      continue;
    }
    const hash = createHash("sha256").update(readFileSync(path.join(raiz, rel))).digest("hex");
    if (hash !== HASH_FAVICON) erros.push(`${rel} hash ${hash}`);
  }
  return erros;
}

export function problemasDist(dir: string) {
  const erros: string[] = [];
  const visitar = (atual: string) => {
    for (const nome of readdirSync(atual)) {
      const caminho = path.join(atual, nome);
      const info = statSync(caminho);
      if (info.isDirectory()) {
        visitar(caminho);
        continue;
      }
      const rel = path.relative(dir, caminho).replaceAll("\\", "/");
      if (nome.endsWith(".svg") && nome !== "favicon.svg") erros.push(rel);
      if (/\.(js|css|html)$/.test(nome)) {
        const texto = readFileSync(caminho, "utf8").toLowerCase();
        if (texto.includes("data:image/svg+xml") || texto.includes("<svg")) erros.push(rel);
      }
    }
  };
  visitar(dir);
  return erros;
}
