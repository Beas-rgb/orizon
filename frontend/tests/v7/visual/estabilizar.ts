import type { Page } from "@playwright/test";

export const FONTES_EXIGIDAS = [
  { familia: "Inter", pesos: [400, 500, 600] },
  { familia: "Montserrat", pesos: [500] },
];

const CSS = `*, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }`;

export async function estabilizar(page: Page) {
  await page.clock.setFixedTime("2026-10-16T12:00:00-03:00");
  await page.addStyleTag({ content: CSS });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolver) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolver()));
    });
  });
}

export async function fontesFaltando(page: Page, exigidas = FONTES_EXIGIDAS) {
  return page.evaluate((lista) => {
    const cobre = (faixa: string, peso: number) => {
      const texto = faixa.trim().toLowerCase();
      if (texto === "normal") return peso === 400;
      if (texto === "bold") return peso === 700;
      const numeros = texto.split(/\s+/).map(Number).filter((n) => !Number.isNaN(n));
      if (numeros.length === 1) return numeros[0] === peso;
      if (numeros.length >= 2) return peso >= numeros[0] && peso <= numeros[1];
      return false;
    };
    const faltou: string[] = [];
    for (const item of lista) {
      for (const peso of item.pesos) {
        const achou = [...document.fonts].some((face) => {
          const familia = face.family.replaceAll('"', "");
          return familia === item.familia && face.status === "loaded" && cobre(face.weight, peso);
        });
        if (!achou) faltou.push(`${item.familia} ${peso}`);
      }
    }
    return faltou;
  }, exigidas);
}

export function origemPermitida(url: string) {
  try {
    return new URL(url).origin === "http://127.0.0.1:4173";
  } catch {
    return false;
  }
}

export async function bloquearRedeExterna(page: Page) {
  await page.route("**/*", (route) => {
    if (origemPermitida(route.request().url())) {
      route.continue();
      return;
    }
    route.abort();
  });
}
