import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiErro, esperaReconexaoMs, sessaoEncerrada } from "./sessaoEstado";
import {
  ATRASO_AVISO_MS,
  LIMITE_MS,
  estadoDoServidor,
  reiniciarAquecimento,
  useServidor,
} from "./servidor";

describe("ApiErro", () => {
  it("separa 401, 500 e rede e preserva a mensagem", () => {
    const acesso = new ApiErro(401, "Sessão inválida.", false);
    const servidor = new ApiErro(500, "Não foi possível concluir.", false);
    const rede = new ApiErro(0, "Sem conexão com o servidor.", true);
    expect(sessaoEncerrada(acesso)).toBe(true);
    expect(sessaoEncerrada(servidor)).toBe(false);
    expect(sessaoEncerrada(rede)).toBe(false);
    expect(rede.rede).toBe(true);
    expect(acesso.message).toBe("Sessão inválida.");
    expect(servidor.message).toBe("Não foi possível concluir.");
  });
});

describe("espera", () => {
  it("segue 2, 4, 8, 16 e 30 segundos", () => {
    expect([1, 2, 3, 4, 5, 6].map(esperaReconexaoMs)).toEqual([
      2000, 4000, 8000, 16000, 30000, 30000,
    ]);
  });
});

describe("servidor", () => {
  it("muda de desconhecido para acordando e depois falha", () => {
    expect(estadoDoServidor(0, false)).toBe("desconhecido");
    expect(estadoDoServidor(ATRASO_AVISO_MS, false)).toBe("acordando");
    expect(estadoDoServidor(LIMITE_MS, false)).toBe("falha");
    expect(estadoDoServidor(LIMITE_MS, true)).toBe("pronto");
  });

  it("mostra acordando depois de 2,5 s sem resposta", async () => {
    reiniciarAquecimento();
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      (_url: string, init: { signal: AbortSignal }) =>
        new Promise((_ok, rejeita) => {
          init.signal.addEventListener("abort", () => rejeita(new Error("abort")));
        }),
    );
    const div = document.createElement("div");
    document.body.appendChild(div);
    const root = createRoot(div);

    function Painel() {
      const { estado } = useServidor();
      return createElement("p", null, estado);
    }

    await act(async () => {
      root.render(createElement(Painel));
    });
    expect(div.textContent).toBe("desconhecido");
    await act(async () => {
      vi.advanceTimersByTime(ATRASO_AVISO_MS);
    });
    expect(div.textContent).toBe("acordando");
    root.unmount();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
});

afterEach(() => {
  reiniciarAquecimento();
});
