import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { raizFront } from "./ajuda";
import { problemasDist } from "./svg-regras";

describe("svg no dist", () => {
  it("reprova svg embutido numa fixture e passa createElement", () => {
    const base = path.join(raizFront, "tests/v7/fixtures/dist-com-svg");
    expect(problemasDist(path.join(base, "data")).length).toBeGreaterThan(0);
    expect(problemasDist(path.join(base, "tag")).length).toBeGreaterThan(0);
    expect(problemasDist(path.join(base, "create"))).toEqual([]);
  });

  it("o dist só tem favicon.svg e não embute svg", () => {
    const dist = path.join(raizFront, "dist");
    if (!existsSync(path.join(dist, "index.html"))) {
      console.warn("dist/ ausente; teste de svg no dist pulado");
      return;
    }
    expect(problemasDist(dist)).toEqual([]);
  });
});
