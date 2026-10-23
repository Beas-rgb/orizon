import { expect, test, type Browser } from "@playwright/test";
import { PNG } from "pngjs";
import { viewportDe } from "./dimensoes";
import { bloquearRedeExterna, estabilizar, FONTES_EXIGIDAS, fontesFaltando } from "./estabilizar";

function iguais(a: Buffer, b: Buffer) {
  if (a.length !== b.length) return false;
  return a.equals(b);
}

async function capturar(browser: Browser, viewport: { width: number; height: number }, caminho: string) {
  const contexto = await browser.newContext({
    viewport,
    deviceScaleFactor: 2,
    timezoneId: "America/Sao_Paulo",
    locale: "pt-BR",
    colorScheme: "light",
    reducedMotion: "reduce",
  });
  const page = await contexto.newPage();
  await bloquearRedeExterna(page);
  await page.goto(caminho);
  await estabilizar(page);
  const png = await page.screenshot({ fullPage: false });
  await contexto.close();
  return png;
}

test("duas capturas no contexto novo são idênticas", async ({ browser }, info) => {
  const largura = info.project.name === "desktop" ? "desktop" : "celular";
  const viewport = viewportDe("01", largura);
  const primeira = PNG.sync.read(await capturar(browser, viewport, "/tests/v7/visual/pagina-fixa.html"));
  const segunda = PNG.sync.read(await capturar(browser, viewport, "/tests/v7/visual/pagina-fixa.html"));
  const faltou = await (async () => {
    const contexto = await browser.newContext({ viewport, deviceScaleFactor: 2 });
    const page = await contexto.newPage();
    await page.goto("/tests/v7/visual/pagina-fixa.html");
    await estabilizar(page);
    const lista = await fontesFaltando(page);
    await contexto.close();
    return lista;
  })();
  expect(faltou, faltou.join(", ")).toEqual([]);
  expect(primeira.width).toBe(segunda.width);
  expect(primeira.height).toBe(segunda.height);
  expect(iguais(primeira.data, segunda.data)).toBe(true);
});

test("um pixel alterado em memória reprova", () => {
  const base = Buffer.from([0, 0, 0, 255, 1, 2, 3, 255]);
  const alterado = Buffer.from(base);
  alterado[0] = 9;
  expect(iguais(base, alterado)).toBe(false);
});

test("família inexistente entra na lista do que faltou", async ({ browser }) => {
  const contexto = await browser.newContext({ viewport: { width: 390, height: 800 }, deviceScaleFactor: 2 });
  const page = await contexto.newPage();
  await page.goto("/tests/v7/visual/pagina-fonte-inexistente.html");
  await estabilizar(page);
  const faltou = await fontesFaltando(page, [{ familia: "HzFonteInexistente", pesos: [400] }]);
  await contexto.close();
  expect(faltou.join(" ")).toContain("HzFonteInexistente");
  expect(FONTES_EXIGIDAS.map((item) => item.familia).sort()).toEqual(["Inter", "Montserrat"]);
});
