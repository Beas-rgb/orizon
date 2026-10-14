import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

/** Diálogo modal acessível: role=dialog, aria-modal, foco inicial no título, Esc fecha. */
export function Dialogo({ titulo, sub, children, rodape, onFechar, largura = 560 }: { titulo: string; sub?: string; children: ReactNode; rodape?: ReactNode; onFechar?: () => void; largura?: number }) {
  const id = useId();
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    ref.current?.focus();
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && onFechar?.();
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [onFechar]);
  return (
    <div className="v7-modal-fundo">
      <div className="v7-modal" role="dialog" aria-modal="true" aria-labelledby={id} style={{ maxWidth: largura }}>
        <div className="v7-modal-cab">
          <div>
            <h2 id={id} ref={ref} tabIndex={-1}>{titulo}</h2>
            {sub ? <p>{sub}</p> : null}
          </div>
          <button type="button" className="v7-btn fantasma" aria-label="Fechar" onClick={onFechar}><X /></button>
        </div>
        <div className="v7-modal-corpo">{children}</div>
        {rodape ? <div className="v7-modal-rodape">{rodape}</div> : null}
      </div>
    </div>
  );
}
