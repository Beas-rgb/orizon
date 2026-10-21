import type { CSSProperties, ReactNode } from "react";

export function Spinner({ grande }: { grande?: boolean }) {
  return (
    <svg className={grande ? "v7-spin g" : "v7-spin"} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
      <path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export function Skeleton({ largura = "100%", altura = 12, estilo }: { largura?: string | number; altura?: number; estilo?: CSSProperties }) {
  return <span className="v7-sk" aria-hidden="true" style={{ width: largura, height: altura, ...estilo }} />;
}

/** Barra com % (valor) ou indeterminada (sem valor). */
export function Progresso({ valor, rotulo }: { valor?: number; rotulo: string }) {
  const ind = valor === undefined;
  return (
    <div
      className={ind ? "v7-pb ind" : "v7-pb"}
      role="progressbar"
      aria-label={rotulo}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={ind ? undefined : valor}
    >
      <i style={ind ? undefined : { width: `${valor}%` }} />
    </div>
  );
}

export function Toast({ children, erro }: { children: ReactNode; erro?: boolean }) {
  return (
    <div className="v7-toast" role={erro ? "alert" : "status"} aria-live={erro ? "assertive" : "polite"}>
      {children}
    </div>
  );
}

export function AnuncioStatus({ texto }: { texto: string }) {
  return (
    <p className="v7-sr" role="status" aria-live="polite">
      {texto}
    </p>
  );
}
