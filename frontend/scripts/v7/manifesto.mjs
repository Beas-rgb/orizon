/**
 * Lê e confere o formato do manifesto. Não recalcula hash e não acessa a rede.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export const TOTAL_LINHAS = 211;

function caminhoManifesto() {
  const candidatos = [
    path.resolve(process.cwd(), "tests/v7/manifesto.json"),
    path.resolve(process.cwd(), "frontend/tests/v7/manifesto.json"),
  ];
  return candidatos.find((candidato) => existsSync(candidato)) ?? candidatos[0];
}

export const CAMINHO_MANIFESTO = caminhoManifesto();

export function lerLinhas(caminho = CAMINHO_MANIFESTO) {
  const bruto = readFileSync(caminho, "utf8").replace(/^\uFEFF/, "");
  const partes = bruto.split(/\r?\n/);
  if (partes.at(-1) === "") partes.pop();
  return partes;
}

export function validarManifesto(caminho = CAMINHO_MANIFESTO) {
  const linhas = lerLinhas(caminho);
  const erros = [];
  if (linhas.length !== TOTAL_LINHAS) {
    erros.push(`o manifesto tem ${linhas.length} linhas; o esperado é ${TOTAL_LINHAS}`);
  }

  const entradas = [];
  const chaves = new Map();
  const hashes = new Map();

  linhas.forEach((linha, indice) => {
    const numero = indice + 1;
    if (linha.trim() === "") {
      erros.push(`linha ${numero} vazia`);
      return;
    }
    let item;
    try {
      item = JSON.parse(linha);
    } catch {
      erros.push(`linha ${numero} não é JSON`);
      return;
    }
    const campos = ["nome", "tela", "largura", "dimensoes", "sha256", "origem"];
    for (const campo of campos) {
      if (typeof item[campo] !== "string" || item[campo].length === 0) {
        erros.push(`linha ${numero} sem ${campo}`);
      }
    }
    if (!/^[0-9a-f]{64}$/.test(item.sha256 ?? "")) {
      erros.push(`linha ${numero} com sha256 fora de 64 hexadecimais`);
    }
    if (item.nome !== `${item.tela}-${item.largura}.png`) {
      erros.push(`linha ${numero} com nome diferente de ${item.tela}-${item.largura}.png`);
    }
    const chave = `${item.tela}|${item.largura}`;
    if (chaves.has(chave)) erros.push(`chave tela+largura repetida: ${chave}`);
    else chaves.set(chave, numero);
    if (typeof item.sha256 === "string") {
      const anteriores = hashes.get(item.sha256) ?? [];
      anteriores.push(chave);
      hashes.set(item.sha256, anteriores);
    }
    entradas.push(item);
  });

  const duplicatas = [...hashes.entries()].filter(([, chavesDoHash]) => chavesDoHash.length > 1);
  if (duplicatas.length) {
    const lista = duplicatas.map(([hash, chavesDoHash]) => `${hash}: ${chavesDoHash.join(", ")}`).join("; ");
    erros.push(`sha256 repetido: ${lista}`);
  }

  return { ok: erros.length === 0, erros, entradas, linhas: linhas.length };
}
