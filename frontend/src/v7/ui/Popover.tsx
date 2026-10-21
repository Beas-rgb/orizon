import { useEffect, useId, useRef, useState, type ReactNode } from "react";

export function Popover({ gatilho, children }: { gatilho: (abrir: () => void, aberto: boolean, id: string) => ReactNode; children: ReactNode }) {
  const [aberto, setAberto] = useState(false);
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false);
    };
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false);
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", tecla);
    };
  }, [aberto]);
  return (
    <div className="v7-pop-wrap" ref={ref}>
      {gatilho(() => setAberto((v) => !v), aberto, id)}
      {aberto ? (
        <div className="v7-pop" id={id} role="dialog">
          {children}
        </div>
      ) : null}
    </div>
  );
}
