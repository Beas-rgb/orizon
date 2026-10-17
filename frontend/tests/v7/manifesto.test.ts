import { describe, expect, it } from "vitest";
import { TOTAL_LINHAS, validarManifesto } from "../../scripts/v7/manifesto.mjs";

describe("formato do manifesto", () => {
  it("tem 211 linhas, hashes únicos e a tela 54 só no celular", () => {
    const resultado = validarManifesto();
    expect(resultado.ok, resultado.erros.join("\n")).toBe(true);
    expect(resultado.linhas).toBe(TOTAL_LINHAS);
    expect(resultado.entradas).toHaveLength(211);

    const porTela = new Map<string, string[]>();
    for (const item of resultado.entradas) {
      const lista = porTela.get(item.tela) ?? [];
      lista.push(item.largura);
      porTela.set(item.tela, lista);
    }
    expect(porTela.size).toBe(106);
    for (let numero = 1; numero <= 106; numero += 1) {
      const tela = String(numero).padStart(2, "0");
      const larguras = [...(porTela.get(tela) ?? [])].sort();
      if (tela === "54") expect(larguras).toEqual(["celular"]);
      else expect(larguras).toEqual(["celular", "desktop"]);
    }

    const porChave = new Map(resultado.entradas.map((item) => [`${item.tela}|${item.largura}`, item]));
    expect(porChave.get("02|celular")?.sha256).toBe("6fdd190f18ccb69b0a5a467816eeb74731e9819bdd10bbe7fd8156dedfe66dad");
    expect(porChave.get("54|celular")?.sha256).toBe("73509e047e6676220bd0792f3a871715b071dcb1df1db91863d15644bbad9163");
    expect(porChave.get("86|desktop")?.sha256).toBe("380adc44c54ac55e44e1e14d3161cdedc3213ed66d2828fd781dc99dd1cbd8ba");
    expect(porChave.get("94|celular")?.sha256).toBe("669b20e10b7ae2ea0d09484d4e61428369f1e859579234ad0e7be565ad291475");
    expect(porChave.get("106|desktop")?.sha256).toBe("62ec89ec6357db5d6c826667a24d17ae923575dc44ffb097c692f4c552a78ee9");
    expect(porChave.has("54|desktop")).toBe(false);
  });
});
