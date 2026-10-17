import { describe, expect, it } from "vitest";
import type { FonteDeDados } from "./dados/FonteDeDados";
import { fonteAlternativa } from "./dados/fonteAlternativa";
import { fonteFicticia } from "./dados/fonteFicticia";
import { regrasDe } from "./ajuda";

describe("fácil de trocar", () => {
  it("reprova hex, rgb, px e cubic-bezier fora dos tokens", () => {
    expect(regrasDe("hex.tsx").achados.some((item) => item.regra === "cor-hex")).toBe(true);
    expect(regrasDe("rgb.tsx").achados.some((item) => item.regra === "cor-rgb")).toBe(true);
    expect(regrasDe("px.tsx").achados.some((item) => item.regra === "cor-px")).toBe(true);
    expect(regrasDe("cubic-bezier.css").achados.some((item) => item.regra === "cor-curva")).toBe(true);
  });

  it("reprova a logo fora do componente Logo e do index.html", () => {
    const duplicada = regrasDe("logo-duplicada");
    expect(duplicada.ok).toBe(false);
    const logos = duplicada.achados.filter((item) => item.regra === "logo");
    expect(logos.length).toBeGreaterThan(0);
    expect(logos.every((item) => item.arquivo.startsWith("telas/"))).toBe(true);
    expect(regrasDe("logo-permitida").ok).toBe(true);
  });

  it("reprova botão estilizado direto numa tela fora de ui", () => {
    const resultado = regrasDe("botao-direto");
    expect(resultado.achados.some((item) => item.regra === "componente")).toBe(true);
  });

  it("reprova import direto de fonteFicticia e aceita a segunda fonte na mesma interface", () => {
    expect(regrasDe("import-fonte").achados.some((item) => item.regra === "fonte-ficticia")).toBe(true);
    expect(regrasDe("import-ok").ok).toBe(true);
    const fontes: FonteDeDados[] = [fonteFicticia, fonteAlternativa];
    expect(fontes.map((fonte) => fonte.ler("65"))).toEqual([
      { nota: 82, oculto: true, desabilitado: false },
      { nota: 10, oculto: false, desabilitado: true },
    ]);
  });
});
