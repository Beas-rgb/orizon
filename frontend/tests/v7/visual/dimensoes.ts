import { readFileSync } from "node:fs";
import path from "node:path";

export type Viewport = { width: number; height: number };

export function interpretarDimensoes(texto: string): Viewport {
  const match = /^(\d+)x(\d+)$/.exec(texto);
  if (!match) throw new Error(`dimensões inválidas: ${texto}`);
  const largura = Number(match[1]);
  const altura = Number(match[2]);
  if (altura % 2 !== 0) throw new Error(`altura ímpar: ${texto}`);
  const width = largura / 2;
  const height = altura / 2;
  if (width !== 390 && width !== 1440) throw new Error(`largura de viewport fora de 390 ou 1440: ${texto}`);
  return { width, height };
}

export function viewportDe(tela: string, largura: string, caminhoManifesto = path.resolve("tests/v7/manifesto.json")): Viewport {
  const linhas = readFileSync(caminhoManifesto, "utf8").split(/\r?\n/).filter(Boolean);
  for (const linha of linhas) {
    const item = JSON.parse(linha) as { tela: string; largura: string; dimensoes: string };
    if (item.tela === tela && item.largura === largura) return interpretarDimensoes(item.dimensoes);
  }
  throw new Error(`manifesto sem ${tela} ${largura}`);
}
