import { execFileSync } from "node:child_process";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { raizFront, regrasDe } from "../ajuda";
import { instalarPageRoute, travarRede, type Pagina, type Rota } from "./rede";

describe("trava de rede", () => {
  it("troca fetch, XHR, WebSocket, EventSource, sendBeacon e api por funções que dão erro", () => {
    const alvo = {
      fetch: () => "ok",
      XMLHttpRequest: function XHR(this: unknown) {
        return this;
      } as unknown as new (...args: unknown[]) => unknown,
      WebSocket: function WS(this: unknown) {
        return this;
      } as unknown as new (...args: unknown[]) => unknown,
      EventSource: function ES(this: unknown) {
        return this;
      } as unknown as new (...args: unknown[]) => unknown,
      navigator: { sendBeacon: () => true },
      api: () => "ok",
    };
    travarRede(alvo);
    expect(() => alvo.fetch("/api")).toThrow(/Rede proibida/);
    expect(() => new alvo.XMLHttpRequest()).toThrow(/Rede proibida/);
    expect(() => new alvo.WebSocket("wss://exemplo")).toThrow(/Rede proibida/);
    expect(() => new alvo.EventSource("/eventos")).toThrow(/Rede proibida/);
    expect(() => alvo.navigator.sendBeacon("/ping")).toThrow(/Rede proibida/);
    expect(() => alvo.api?.("/projetos")).toThrow(/Rede proibida/);
  });

  it("page.route reprova qualquer URL", () => {
    let tratar: ((rota: Rota) => void) | undefined;
    let padrao = "";
    const pagina: Pagina = {
      route(recebido, fn) {
        padrao = recebido;
        tratar = fn;
      },
    };
    instalarPageRoute(pagina);
    expect(padrao).toBe("**/*");
    for (const url of ["https://exemplo.com", "http://127.0.0.1:8000/auth", "/assets/logo/horizon-logo.png", "ws://localhost/ao-vivo"]) {
      let abortou = false;
      tratar?.({
        url: () => url,
        abort() {
          abortou = true;
        },
      });
      expect(abortou).toBe(true);
    }
  });

  it("reprova um arquivo de exemplo com fetch", () => {
    const resultado = regrasDe("fetch.tsx");
    expect(resultado.ok).toBe(false);
    expect(resultado.achados.map((item) => item.regra)).toEqual(expect.arrayContaining(["fetch", "url"]));
    const cli = path.join(raizFront, "scripts/v7/varredura.mjs");
    expect(() =>
      execFileSync(process.execPath, [cli, "--raiz", path.join(raizFront, "tests/v7/fixtures/fetch.tsx")], {
        encoding: "utf8",
      }),
    ).toThrow();
  });
});
