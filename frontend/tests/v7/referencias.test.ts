import { mkdtempSync, mkdirSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { lerLinhas } from "../../scripts/v7/manifesto.mjs";
import { raizFront } from "./ajuda";

function nomesDoManifesto() {
  return new Set(lerLinhas().map((linha: string) => JSON.parse(linha).nome as string));
}

export function pngForaDoLugar(raiz: string, nomes: Set<string>) {
  const erros: string[] = [];
  const visitar = (dir: string) => {
    let entradas: string[];
    try {
      entradas = readdirSync(dir);
    } catch {
      return;
    }
    for (const nome of entradas) {
      if (nome === "node_modules" || nome === "dist") continue;
      const caminho = path.join(dir, nome);
      const info = statSync(caminho);
      const rel = path.relative(raiz, caminho).replaceAll("\\", "/");
      if (info.isDirectory()) {
        visitar(caminho);
        continue;
      }
      if (!nome.endsWith(".png") || !nomes.has(nome)) continue;
      if (!rel.startsWith("tests/v7/referencias/")) erros.push(rel);
    }
  };
  visitar(raiz);
  return erros;
}

export function pngDesconhecido(arquivos: string[], nomes: Set<string>) {
  return arquivos.filter((nome) => !nomes.has(nome));
}

describe("referências fora da pasta", () => {
  it("reprova um png do manifesto fora de tests/v7/referencias e um nome desconhecido dentro", () => {
    const nomes = nomesDoManifesto();
    expect(pngForaDoLugar(raizFront, nomes)).toEqual([]);
    const temp = mkdtempSync(path.join(tmpdir(), "hz-refs-"));
    writeFileSync(path.join(temp, "01-celular.png"), "fora");
    mkdirSync(path.join(temp, "tests/v7/referencias"), { recursive: true });
    writeFileSync(path.join(temp, "tests/v7/referencias/extra.png"), "dentro");
    expect(pngForaDoLugar(temp, nomes)).toEqual(["01-celular.png"]);
    expect(pngDesconhecido(["extra.png"], nomes)).toEqual(["extra.png"]);
  });
});
