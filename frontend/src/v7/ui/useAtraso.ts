import { useEffect, useState } from "react";

/** Só mostra o indicador depois de 300 ms (evita piscar). */
export function useAtraso(ativo: boolean, ms = 300) {
  const [ver, setVer] = useState(false);
  useEffect(() => {
    if (!ativo) return;
    const t = window.setTimeout(() => setVer(true), ms);
    return () => {
      window.clearTimeout(t);
      setVer(false);
    };
  }, [ativo, ms]);
  return ativo && ver;
}
