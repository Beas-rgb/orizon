import { describe, expect, it } from "vitest";
import { origemPermitida } from "./visual/estabilizar";

describe("origem da rede", () => {
  it("barra o host parecido e deixa só a porta 4173", () => {
    expect(origemPermitida("http://127.0.0.1.exemplo.com/")).toBe(false);
    expect(origemPermitida("http://127.0.0.1:4173/")).toBe(true);
  });
});