import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { comparar, criarImagem, pintarQuadrado } from "./comparar";
import { MANCHA_MAXIMA_PX, TOLERANCIA_PERCENTUAL } from "./tolerancia";

const branco: [number, number, number, number] = [255, 255, 255, 255];
const preto: [number, number, number, number] = [0, 0, 0, 255];

describe("comparador", () => {
  it("mantém 0,5% e mancha de 8 px, e reprova se o arquivo mudar esses valores", () => {
    const fonte = readFileSync(path.join(process.cwd(), "tests/v7/comparador/tolerancia.ts"), "utf8").replaceAll("\r\n", "\n");
    expect(TOLERANCIA_PERCENTUAL).toBe(0.005);
    expect(MANCHA_MAXIMA_PX).toBe(8);
    expect(fonte).toContain("export const TOLERANCIA_PERCENTUAL = 0.005;");
    expect(fonte).toContain("export const MANCHA_MAXIMA_PX = 8;");
  });

  it("passa com mancha de 8×8 e reprova com mancha de 9×9", () => {
    const base = criarImagem(200, 200, branco);
    const oito = comparar(base, pintarQuadrado(base, 10, 10, 8, preto));
    const nove = comparar(base, pintarQuadrado(base, 10, 10, 9, preto));
    expect(oito.passou).toBe(true);
    expect(oito.manchaLargura).toBe(8);
    expect(oito.manchaAltura).toBe(8);
    expect(nove.passou).toBe(false);
    expect(nove.manchaLargura).toBe(9);
    expect(nove.manchaAltura).toBe(9);
  });

  it("reprova diferença acima de 0,5% mesmo com manchas de 1 px e não corta tamanho diferente", () => {
    const base = criarImagem(200, 200, branco);
    const pixels = new Uint8ClampedArray(base.pixels);
    let pintados = 0;
    for (let y = 0; y < 200 && pintados < 240; y += 2) {
      for (let x = 0; x < 200 && pintados < 240; x += 2) {
        const i = (y * 200 + x) * 4;
        pixels[i] = 0;
        pintados += 1;
      }
    }
    const espalhado = comparar(base, { largura: 200, altura: 200, pixels });
    expect(espalhado.manchaLargura).toBe(1);
    expect(espalhado.passou).toBe(false);
    const menor = criarImagem(199, 200, branco);
    expect(comparar(base, menor).motivos[0]).toMatch(/não corta nem estica/);
  });
});
