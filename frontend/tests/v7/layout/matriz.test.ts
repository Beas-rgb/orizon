import { describe, expect, it } from "vitest";
import { avaliarMedida, CORTE_DESKTOP_PX, layoutDe, LARGURAS_PX } from "./matriz";

describe("matriz de larguras", () => {
  it("corta em 1024 e reprova rolagem, texto cortado ou toque curto", () => {
    expect(LARGURAS_PX).toEqual([759, 760, 761, 768, 1023, 1024, 1025]);
    expect(CORTE_DESKTOP_PX).toBe(1024);
    expect(layoutDe(1023)).toBe("celular");
    expect(layoutDe(1024)).toBe("desktop");
    expect(avaliarMedida({ largura: 1024, rolagemLateral: false, textoCortado: false, menorAlvoPx: 44 })).toEqual([]);
    expect(avaliarMedida({ largura: 760, rolagemLateral: true, textoCortado: false, menorAlvoPx: 44 })).toContain("rolagem lateral");
    expect(avaliarMedida({ largura: 768, rolagemLateral: false, textoCortado: true, menorAlvoPx: 44 })).toContain("texto cortado");
    expect(avaliarMedida({ largura: 390, rolagemLateral: false, textoCortado: false, menorAlvoPx: 40 }).length).toBeGreaterThan(0);
  });
});
