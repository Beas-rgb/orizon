import { useCallback, useEffect, useState } from "react";
import { urlApi } from "./api";

export type EstadoServidor = "desconhecido" | "acordando" | "pronto" | "falha";

export const ATRASO_AVISO_MS = 2500;
export const INTERVALO_MS = 3000;
export const LIMITE_MS = 90_000;
export const TIMEOUT_HEALTH_MS = 8000;

let visitaAquecida = false;

export function estadoDoServidor(decorridoMs: number, ok: boolean): EstadoServidor {
  if (ok) return "pronto";
  if (decorridoMs >= LIMITE_MS) return "falha";
  if (decorridoMs >= ATRASO_AVISO_MS) return "acordando";
  return "desconhecido";
}

export async function aquecerServidor(timeoutMs = TIMEOUT_HEALTH_MS): Promise<boolean> {
  const controle = new AbortController();
  const prazo = setTimeout(() => controle.abort(), timeoutMs);
  try {
    const resposta = await fetch(urlApi("/health"), { signal: controle.signal });
    return resposta.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(prazo);
  }
}

export function useServidor() {
  const [estado, setEstado] = useState<EstadoServidor>("desconhecido");
  const [ciclo, setCiclo] = useState(0);

  const tentarDeNovo = useCallback(() => {
    visitaAquecida = false;
    setEstado("desconhecido");
    setCiclo((valor) => valor + 1);
  }, []);

  useEffect(() => {
    if (visitaAquecida) {
      setEstado("pronto");
      return;
    }
    let vivo = true;
    const inicio = Date.now();
    let proximo = 0;
    const aviso = window.setTimeout(() => {
      if (!vivo) return;
      setEstado((atual) => (atual === "desconhecido" ? "acordando" : atual));
    }, ATRASO_AVISO_MS);

    async function pulso() {
      const ok = await aquecerServidor();
      if (!vivo) return;
      if (ok) {
        visitaAquecida = true;
        setEstado("pronto");
        return;
      }
      const decorrido = Date.now() - inicio;
      if (decorrido >= LIMITE_MS) {
        setEstado("falha");
        return;
      }
      proximo = window.setTimeout(() => void pulso(), INTERVALO_MS);
    }

    void pulso();
    return () => {
      vivo = false;
      window.clearTimeout(aviso);
      window.clearTimeout(proximo);
    };
  }, [ciclo]);

  return { estado, tentarDeNovo };
}
