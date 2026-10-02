import { ApiErro } from "./sessaoEstado";

export const ESPERAS_RAJADA_S = [2, 4, 8, 16, 30] as const;

export type OpcoesRetry = {
  max?: number;
  dormir?: (ms: number) => Promise<void>;
  aleatorio?: () => number;
  aoEsperar?: () => void;
};

export type SaidaRetry<T> = { valor: T | null; jaRegistrada: boolean };

const dormirPadrao = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function deveRepetir(erro: unknown): boolean {
  if (!(erro instanceof ApiErro)) return false;
  if (erro.status === 409 || erro.status === 422 || erro.status === 404 || erro.status === 403) {
    return false;
  }
  return erro.status === 503 || erro.status === 429 || erro.status === 0 || erro.rede;
}

export function esperaRajadaMs(
  tentativa: number,
  aleatorio: () => number = Math.random,
  retryAfterSegundos: number | null = null,
): number {
  if (retryAfterSegundos != null && retryAfterSegundos >= 0) {
    return Math.round(retryAfterSegundos * 1000);
  }
  const indice = Math.min(Math.max(tentativa, 1), ESPERAS_RAJADA_S.length) - 1;
  const fator = 0.7 + aleatorio() * 0.6;
  return Math.round(ESPERAS_RAJADA_S[indice] * 1000 * fator);
}

export async function enviarComRetry<T>(
  fn: () => Promise<T>,
  opcoes: OpcoesRetry = {},
): Promise<SaidaRetry<T>> {
  const max = opcoes.max ?? 5;
  const dormir = opcoes.dormir ?? dormirPadrao;
  const aleatorio = opcoes.aleatorio ?? Math.random;
  let ultimo: unknown;
  for (let tentativa = 1; tentativa <= max; tentativa += 1) {
    try {
      return { valor: await fn(), jaRegistrada: false };
    } catch (erro) {
      if (erro instanceof ApiErro && erro.status === 409) {
        return { valor: null, jaRegistrada: true };
      }
      ultimo = erro;
      if (!deveRepetir(erro) || tentativa === max) throw erro;
      opcoes.aoEsperar?.();
      const esperaHeader = erro instanceof ApiErro ? erro.retryAfter : null;
      await dormir(esperaRajadaMs(tentativa, aleatorio, esperaHeader));
    }
  }
  throw ultimo;
}
