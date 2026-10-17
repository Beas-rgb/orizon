import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { varrer } from "../../scripts/v7/varredura.mjs";
import { variaveisCss } from "../../src/v7/tokens/tokens";
import { raizFront } from "./ajuda";

describe("tokens", () => {
  it("repete no CSS e no TS os valores do design e a varredura de src/v7 passa", () => {
    const css = readFileSync(path.join(raizFront, "src/v7/tokens/tokens.css"), "utf8");
    const lidos = new Map<string, string>();
    for (const linha of css.split("\n")) {
      const match = linha.match(/^\s*(--hz-[a-z0-9-]+)\s*:\s*(.*);\s*$/);
      if (!match) continue;
      lidos.set(match[1], match[2].replaceAll("\\;", ";").trim());
    }
    expect(lidos.size).toBe(Object.keys(variaveisCss).length);
    for (const [nome, valor] of Object.entries(variaveisCss)) {
      expect(lidos.get(nome)).toBe(valor);
    }
    expect(variaveisCss["--hz-brand"]).toBe("#1D5FAF");
    expect(Object.values(variaveisCss)).toContain("cubic-bezier(.2,.7,.2,1)");
    expect(varrer(path.join(raizFront, "src/v7")).ok).toBe(true);
  });
});
