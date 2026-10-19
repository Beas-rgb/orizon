import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { tokensInvalidos } from "../../scripts/v7/gerar-tokens.mjs";
import { raizFront } from "./ajuda";

function nomes(entradas: { nome: string; valor: string }[]) {
  return tokensInvalidos(entradas).map((item) => item.nome);
}

describe("validade dos tokens", () => {
  it("reprova cada regra em memória", () => {
    expect(nomes([{ nome: "--hz-a", valor: "--hz-ink" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-a", valor: "rgb(1, 2" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-a", valor: "1px\\;" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-a", valor: "@media (max-width:1px)" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-a", valor: "@supports (color:red)" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-a", valor: "1 → 2" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-a", valor: "1 — 2" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-a", valor: "1 · 2" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-espaco", valor: "12" }])).toContain("--hz-espaco");
    expect(nomes([{ nome: "--hz-tipo-peso", valor: "600" }])).toEqual([]);
    expect(nomes([{ nome: "--hz-a", valor: "tela cheia" }])).toContain("--hz-a");
    expect(nomes([{ nome: "--hz-tipo-ate-760px-tamanho", valor: "22px" }])).toContain("--hz-tipo-ate-760px-tamanho");
  });

  it("aceita o tokens.css gerado", () => {
    const css = readFileSync(path.join(raizFront, "src/v7/tokens/tokens.css"), "utf8");
    const entradas = [];
    for (const linha of css.split("\n")) {
      const match = linha.match(/^\s*(--hz-[a-z0-9-]+)\s*:\s*(.*);\s*$/);
      if (match) entradas.push({ nome: match[1], valor: match[2] });
    }
    expect(tokensInvalidos(entradas)).toEqual([]);
  });
});
