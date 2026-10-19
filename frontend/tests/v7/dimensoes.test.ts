import { describe, expect, it } from "vitest";
import { interpretarDimensoes, viewportDe } from "./visual/dimensoes";

describe("dimensões do manifesto", () => {
  it("divide três linhas por 2 e recusa largura ou altura inválida", () => {
    expect(viewportDe("01", "celular")).toEqual({ width: 390, height: 1414 });
    expect(viewportDe("01", "desktop")).toEqual({ width: 1440, height: 900 });
    expect(viewportDe("02", "celular")).toEqual({ width: 390, height: 844 });
    expect(() => interpretarDimensoes("800x1000")).toThrow(/390 ou 1440/);
    expect(() => interpretarDimensoes("780x1689")).toThrow(/ímpar/);
  });
});
