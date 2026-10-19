import { describe, expect, it } from "vitest";
import { exibirComoVeio } from "./exibirComoVeio";

describe("JSON incoerente", () => {
  it("mostra a nota, o oculto e o desabilitado como vieram, sem recalcular", () => {
    const json = { nota: 999, oculto: false, desabilitado: false, avaliadores: 2 };
    expect(exibirComoVeio(json)).toEqual({ nota: 999, oculto: false, desabilitado: false });
  });
});
