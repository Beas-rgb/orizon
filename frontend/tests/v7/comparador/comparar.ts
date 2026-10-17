import { MANCHA_MAXIMA_PX, TOLERANCIA_PERCENTUAL } from "./tolerancia";

export type Imagem = {
  largura: number;
  altura: number;
  pixels: Uint8ClampedArray;
};

export type ResultadoComparacao = {
  passou: boolean;
  percentual: number;
  manchaLargura: number;
  manchaAltura: number;
  motivos: string[];
};

export function criarImagem(
  largura: number,
  altura: number,
  cor: [number, number, number, number],
): Imagem {
  const pixels = new Uint8ClampedArray(largura * altura * 4);
  for (let i = 0; i < pixels.length; i += 4) {
    pixels[i] = cor[0];
    pixels[i + 1] = cor[1];
    pixels[i + 2] = cor[2];
    pixels[i + 3] = cor[3];
  }
  return { largura, altura, pixels };
}

export function pintarQuadrado(
  base: Imagem,
  x0: number,
  y0: number,
  lado: number,
  cor: [number, number, number, number],
): Imagem {
  const pixels = new Uint8ClampedArray(base.pixels);
  for (let y = y0; y < y0 + lado; y += 1) {
    for (let x = x0; x < x0 + lado; x += 1) {
      const i = (y * base.largura + x) * 4;
      pixels[i] = cor[0];
      pixels[i + 1] = cor[1];
      pixels[i + 2] = cor[2];
      pixels[i + 3] = cor[3];
    }
  }
  return { largura: base.largura, altura: base.altura, pixels };
}

function diferente(a: Uint8ClampedArray, b: Uint8ClampedArray, i: number) {
  return a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2] || a[i + 3] !== b[i + 3];
}

export function comparar(referencia: Imagem, atual: Imagem): ResultadoComparacao {
  const motivos: string[] = [];
  if (referencia.largura !== atual.largura || referencia.altura !== atual.altura) {
    return {
      passou: false,
      percentual: 1,
      manchaLargura: 0,
      manchaAltura: 0,
      motivos: ["dimensões diferentes; o comparador não corta nem estica"],
    };
  }

  const { largura, altura } = referencia;
  const total = largura * altura;
  const difere = new Uint8Array(total);
  let diferentes = 0;
  for (let p = 0; p < total; p += 1) {
    if (diferente(referencia.pixels, atual.pixels, p * 4)) {
      difere[p] = 1;
      diferentes += 1;
    }
  }

  const visto = new Uint8Array(total);
  let manchaLargura = 0;
  let manchaAltura = 0;
  const fila: number[] = [];
  for (let inicio = 0; inicio < total; inicio += 1) {
    if (!difere[inicio] || visto[inicio]) continue;
    let minX = largura;
    let maxX = 0;
    let minY = altura;
    let maxY = 0;
    fila.push(inicio);
    visto[inicio] = 1;
    for (let cursor = 0; cursor < fila.length; cursor += 1) {
      const p = fila[cursor];
      const x = p % largura;
      const y = Math.floor(p / largura);
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      const vizinhos = [p - 1, p + 1, p - largura, p + largura];
      for (const vizinho of vizinhos) {
        if (vizinho < 0 || vizinho >= total || visto[vizinho] || !difere[vizinho]) continue;
        const vx = vizinho % largura;
        if (Math.abs(vx - x) > 1) continue;
        visto[vizinho] = 1;
        fila.push(vizinho);
      }
    }
    fila.length = 0;
    const w = maxX - minX + 1;
    const h = maxY - minY + 1;
    if (w > manchaLargura) manchaLargura = w;
    if (h > manchaAltura) manchaAltura = h;
  }

  const percentual = diferentes / total;
  if (percentual > TOLERANCIA_PERCENTUAL) {
    motivos.push(`diferença ${percentual} acima de ${TOLERANCIA_PERCENTUAL}`);
  }
  if (manchaLargura > MANCHA_MAXIMA_PX || manchaAltura > MANCHA_MAXIMA_PX) {
    motivos.push(`mancha ${manchaLargura}×${manchaAltura} acima de ${MANCHA_MAXIMA_PX}×${MANCHA_MAXIMA_PX}`);
  }

  return { passou: motivos.length === 0, percentual, manchaLargura, manchaAltura, motivos };
}
