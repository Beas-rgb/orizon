import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { gerarDeJson } from "../../scripts/v7/gerar-tokens.mjs";
import { raizFront } from "./ajuda";

describe("gerador de tokens", () => {
  it("reproduz os arquivos commitados", () => {
    const json = JSON.parse(readFileSync(path.join(raizFront, "scripts/v7/tokens-final-2026-10-16.json"), "utf8"));
    const gerado = gerarDeJson(json);
    const dir = path.join(raizFront, "src/v7/tokens");
    expect(gerado.css).toBe(readFileSync(path.join(dir, "tokens.css"), "utf8"));
    expect(gerado.ts).toBe(readFileSync(path.join(dir, "tokens.ts"), "utf8"));
    expect(gerado.regras).toBe(readFileSync(path.join(dir, "REGRAS.md"), "utf8"));
  });

  it("reprova um tokens.css editado à mão", () => {
    const json = JSON.parse(readFileSync(path.join(raizFront, "scripts/v7/tokens-final-2026-10-16.json"), "utf8"));
    const gerado = gerarDeJson(json);
    expect(gerado.css.replace("#1D5FAF", "#000000")).not.toBe(gerado.css);
  });
});
