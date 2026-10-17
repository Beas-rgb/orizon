import { describe, expect, it } from "vitest";
import { avaliarDesempenho, relatorioNoLimite } from "./limites";

describe("limites de desempenho", () => {
  it("aceita o limite e reprova um relatório plantado acima dele", () => {
    expect(avaliarDesempenho(relatorioNoLimite())).toEqual([]);
    const ruim = { ...relatorioNoLimite(), jsInicialGzipKb: 121, cls: 0.06, performance: 89 };
    const erros = avaliarDesempenho(ruim);
    expect(erros).toEqual(expect.arrayContaining(["js inicial", "cls", "performance"]));
  });
});
