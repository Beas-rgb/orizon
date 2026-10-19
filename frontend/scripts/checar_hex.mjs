/**
 * Falha se aparecer cor solta fora de src/styles/tokens.css.
 * scripts/hex_legado.txt lista o que ainda não migrou. A lista só pode diminuir.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const raizFrontend = fileURLToPath(new URL("..", import.meta.url));
const lista = join(raizFrontend, "scripts", "hex_legado.txt");
const cor = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/;

const args = process.argv.slice(2);
const indice = args.indexOf("--raiz");
let raiz = raizFrontend;
let pasta = "src";
if (indice >= 0) {
  const valor = args[indice + 1];
  if (!valor || valor.startsWith("--")) {
    console.error("--raiz precisa de uma pasta");
    process.exit(2);
  }
  raiz = resolve(valor);
  pasta = "src";
}

const src = join(raiz, "src");

function arquivos(dir, saida = []) {
  for (const nome of readdirSync(dir)) {
    const caminho = join(dir, nome);
    if (statSync(caminho).isDirectory()) arquivos(caminho, saida);
    else if (/\.(ts|tsx|css)$/.test(nome)) saida.push(caminho);
  }
  return saida;
}

const legado = new Set(
  readFileSync(lista, "utf8")
    .split(/\r?\n/)
    .map((linha) => linha.trim())
    .filter((linha) => linha && !linha.startsWith("#")),
);

const achados = [];
for (const arquivo of arquivos(src)) {
  const rel = relative(raiz, arquivo).replaceAll("\\", "/");
  if (rel === "src/styles/tokens.css" || rel.startsWith("src/v7/tokens/") || legado.has(rel)) continue;
  const linhas = readFileSync(arquivo, "utf8").split(/\r?\n/);
  linhas.forEach((texto, i) => {
    if (cor.test(texto)) achados.push(`${rel}:${i + 1}`);
  });
}

if (achados.length) {
  console.error(achados.join("\n"));
  process.exit(1);
}
console.log(`hex ok; legado=${legado.size}; pasta=${pasta}`);
