import { describe, expect, it } from "vitest";
import { DOMINIOS_EMAIL } from "../../../scripts/v7/varredura.mjs";
import { regrasDe } from "../ajuda";

describe("travas de lógica, e-mail e proibições", () => {
  it("aceita só os 5 domínios e reprova e-mail externo", () => {
    expect(DOMINIOS_EMAIL).toEqual([
      "orgao.exemplo.gov.br",
      "consultoria.exemplo.gov.br",
      "saude.rioclaro.exemplo.gov.br",
      "valeazul.exemplo.gov.br",
      "horizon.exemplo.gov.br",
    ]);
    const externo = regrasDe("email-externo.ts");
    expect(externo.ok).toBe(false);
    expect(externo.achados.some((item) => item.regra === "email")).toBe(true);
    expect(regrasDe("email-reticencias.ts").ok).toBe(true);
  });

  it("deixa passar o namespace SVG e o xlink", () => {
    expect(regrasDe("namespace-svg.ts").ok).toBe(true);
  });

  it("reprova lógica de negócio plantada", () => {
    const regras = new Set(regrasDe("logica-negocio.ts").achados.map((item) => item.regra));
    expect(regras).toEqual(
      new Set(["logica-reduce", "logica-math", "logica-piso", "logica-perfil", "logica-role"]),
    );
  });

  it("reprova o CPF 111.111.111-11 marcado como inválido", () => {
    const resultado = regrasDe("cpf-invalido.ts");
    expect(resultado.achados.some((item) => item.regra === "cpf-invalido")).toBe(true);
  });

  it("reprova eval, Function, html inseguro, serviço, push, manifesto e console da ação", () => {
    const regras = new Set(regrasDe("proibidos.ts").achados.map((item) => item.regra));
    for (const regra of ["eval", "new-function", "localStorage", "axios", "service-worker", "push", "pwa", "console-acao", "html-inseguro"]) {
      expect(regras.has(regra)).toBe(true);
    }
  });

  it("reprova import que sai de src/v7 e aceita import interno", () => {
    expect(regrasDe("import-fora/src/v7").ok).toBe(false);
    expect(regrasDe("import-fora/src/v7").achados.some((item) => item.regra === "import-fora")).toBe(true);
    expect(regrasDe("import-interno/src/v7").ok).toBe(true);
  });
});
