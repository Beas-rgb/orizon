import { useCallback, useEffect, useState } from "react";

/** Estado do menu suspenso: aberto por hover, foco ou clique; Esc fecha e devolve o foco. */
export function useMenuAberto(devolverFoco?: () => void) {
  const [hover, setHover] = useState(false);
  const [foco, setFoco] = useState(false);
  const [preso, setPreso] = useState(false);
  const aberto = hover || foco || preso;
  const fechar = useCallback(() => {
    setHover(false);
    setFoco(false);
    setPreso(false);
    (document.activeElement as HTMLElement | null)?.blur?.();
  }, []);
  useEffect(() => {
    if (!aberto) return;
    const tecla = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      fechar();
      devolverFoco?.();
    };
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [aberto, fechar, devolverFoco]);
  return { aberto, preso, setHover, setFoco, setPreso, fechar };
}
