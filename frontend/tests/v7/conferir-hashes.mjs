/**
 * Recalcula o sha256 dos PNG na pasta plana apontada por HZ_REFERENCIAS_DIR.
 * Não roda no npm test, não acessa a rede e não lê nada fora dessa pasta.
 * Cada arquivo se chama <tela>-<largura>.png.
 */
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { validarManifesto } from "../../scripts/v7/manifesto.mjs";

const pasta = process.env.HZ_REFERENCIAS_DIR;

if (!pasta) {
  console.error(
    "HZ_REFERENCIAS_DIR não está definida. Aponte para a pasta plana local com os 211 arquivos <tela>-<largura>.png. Este script não acessa a rede.",
  );
  process.exit(1);
}

let info;
try {
  info = statSync(pasta);
} catch {
  console.error(
    `Pasta não encontrada: ${pasta}. HZ_REFERENCIAS_DIR precisa ser o caminho de uma pasta plana local. Este script não acessa a rede.`,
  );
  process.exit(1);
}

if (!info.isDirectory()) {
  console.error(`HZ_REFERENCIAS_DIR não é uma pasta: ${pasta}`);
  process.exit(1);
}

const formato = validarManifesto();
if (!formato.ok) {
  console.error(formato.erros.join("\n"));
  process.exit(1);
}

const presentes = new Set(
  readdirSync(pasta).filter((nome) => nome.toLowerCase().endsWith(".png")),
);
const esperados = new Set(formato.entradas.map((item) => item.nome));
const erros = [];

for (const nome of esperados) {
  if (!presentes.has(nome)) erros.push(`falta ${nome}`);
}
for (const nome of presentes) {
  if (!esperados.has(nome)) erros.push(`sobra ${nome}`);
}

for (const item of formato.entradas) {
  if (!presentes.has(item.nome)) continue;
  const bytes = readFileSync(path.join(pasta, item.nome));
  const hash = createHash("sha256").update(bytes).digest("hex");
  if (hash !== item.sha256) erros.push(`diverge ${item.nome}`);
}

if (erros.length) {
  console.error(`referências reprovadas (${erros.length}):`);
  console.error(erros.join("\n"));
  process.exit(1);
}

console.log(`hashes ok (${formato.entradas.length})`);
