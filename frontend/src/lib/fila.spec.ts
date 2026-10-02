import { describe, expect, it } from "vitest";
import { ApiErro } from "./sessaoEstado";
import { deveRepetir, enviarComRetry, esperaRajadaMs } from "./fila";

describe("fila de resposta", () => {
  it("não repete 422, 404 nem 403", async () => {
    for (const status of [422, 404, 403]) {
      let chamadas = 0;
      await expect(
        enviarComRetry(async () => {
          chamadas += 1;
          throw new ApiErro(status, "invalido");
        }, { dormir: async () => undefined }),
      ).rejects.toMatchObject({ status });
      expect(chamadas).toBe(1);
      expect(deveRepetir(new ApiErro(status, "x"))).toBe(false);
    }
  });

  it("trata 409 como sucesso", async () => {
    let chamadas = 0;
    const saida = await enviarComRetry(async () => {
      chamadas += 1;
      throw new ApiErro(409, "já");
    });
    expect(saida.jaRegistrada).toBe(true);
    expect(chamadas).toBe(1);
  });

  it("deixa o jitter entre 0,7 e 1,3 e respeita Retry-After", () => {
    const baixo = esperaRajadaMs(1, () => 0);
    const alto = esperaRajadaMs(1, () => 0.999);
    expect(baixo).toBe(1400);
    expect(alto).toBeGreaterThanOrEqual(2000 * 1.2);
    expect(alto).toBeLessThanOrEqual(2000 * 1.3);
    expect(esperaRajadaMs(1, () => 0, 3)).toBe(3000);
  });

  it("para na quinta tentativa", async () => {
    let chamadas = 0;
    const esperas: number[] = [];
    await expect(
      enviarComRetry(
        async () => {
          chamadas += 1;
          throw new ApiErro(503, "ocupado");
        },
        {
          max: 5,
          aleatorio: () => 0.5,
          dormir: async (ms) => {
            esperas.push(ms);
          },
        },
      ),
    ).rejects.toMatchObject({ status: 503 });
    expect(chamadas).toBe(5);
    expect(esperas).toHaveLength(4);
  });
});
