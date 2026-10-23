import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { raizFront } from "./ajuda";
import { listarSvg, problemasSvg, svgForaDaAllowlist } from "./svg-regras";

describe("SVG", () => {
  it("só permite o favicon com o hash congelado", () => {
    const arquivos = listarSvg(raizFront);
    expect(svgForaDaAllowlist(arquivos, raizFront)).toEqual([]);
    expect(svgForaDaAllowlist(["public/favicon.svg", "public/outro.svg"], raizFront)).toContain("public/outro.svg");
  });

  it("reprova cada fixture de conteúdo", () => {
    const pasta = path.join(raizFront, "tests/v7/fixtures/svg");
    const casos = ["com-script.svg", "foreign.svg", "onload.svg", "href-externo.svg", "url-externo.svg", "import.svg", "entity.svg"];
    for (const nome of casos) {
      const erros = problemasSvg(readFileSync(path.join(pasta, nome), "utf8"));
      expect(erros.length, nome).toBeGreaterThan(0);
    }
  });
});
