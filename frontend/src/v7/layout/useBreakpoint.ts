import { useSyncExternalStore } from "react";

/** Um único corte: < 900 px = celular (gaveta + barra inferior); ≥ 900 px = desktop (menu fixo no canto). */
export const CORTE_DESKTOP = 900;
const consulta = `(min-width: ${CORTE_DESKTOP}px)`;

function assinar(aviso: () => void) {
  const m = window.matchMedia(consulta);
  m.addEventListener("change", aviso);
  return () => m.removeEventListener("change", aviso);
}

export function useEhDesktop() {
  return useSyncExternalStore(assinar, () => window.matchMedia(consulta).matches, () => true);
}
