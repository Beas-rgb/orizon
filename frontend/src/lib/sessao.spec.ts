import { afterEach, describe, expect, it, vi } from "vitest";
import { api, limparSessao } from "./api";
import { liberarRefresh, renovarSessao } from "./sessao";

function json(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  limparSessao();
  liberarRefresh();
  vi.unstubAllGlobals();
});

describe("refresh", () => {
  it("cinco 401 simultâneos renovam uma vez e repetem a chamada", async () => {
    sessionStorage.setItem("horizon_refresh", "refresh-1");
    sessionStorage.setItem("horizon_access", "access-1");
    let refresh = 0;
    vi.stubGlobal("fetch", async (url: string) => {
      if (String(url).includes("/auth/refresh")) {
        refresh += 1;
        await new Promise((resolver) => setTimeout(resolver, 20));
        return json(200, {
          access_token: "access-2",
          refresh_token: "refresh-2",
          painel: "dev",
          usuario: { id: "1", nome: "Ana", email: "ana@horizon.dev", painel: "dev" },
        });
      }
      if (sessionStorage.getItem("horizon_access") === "access-1") {
        return json(401, { detail: "Não autenticado." });
      }
      return json(200, { ok: true });
    });
    const respostas = await Promise.all(
      [1, 2, 3, 4, 5].map(() => api<{ ok: boolean }>("/projetos")),
    );
    expect(refresh).toBe(1);
    expect(respostas.every((item) => item.ok)).toBe(true);
  });

  it("refresh 401 dispara o evento e limpa a sessão", async () => {
    sessionStorage.setItem("horizon_refresh", "refresh-1");
    let eventos = 0;
    window.addEventListener("horizon:sessao-expirada", () => {
      eventos += 1;
    });
    vi.stubGlobal("fetch", async () => json(401, { detail: "Sessão inválida." }));
    await expect(renovarSessao()).rejects.toMatchObject({ status: 401 });
    expect(eventos).toBe(1);
    expect(sessionStorage.getItem("horizon_refresh")).toBeNull();
  });

  it("rede no refresh mantém os tokens", async () => {
    sessionStorage.setItem("horizon_refresh", "refresh-1");
    sessionStorage.setItem("horizon_access", "access-1");
    vi.stubGlobal("fetch", async () => {
      throw new Error("offline");
    });
    await expect(renovarSessao()).rejects.toMatchObject({ rede: true, status: 0 });
    expect(sessionStorage.getItem("horizon_refresh")).toBe("refresh-1");
  });
});
