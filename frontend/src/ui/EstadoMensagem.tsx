import type { ReactNode } from "react";

type Tom = "neutro" | "erro" | "ok" | "aviso";

const tomClasse: Record<Tom, string> = {
  neutro: "text-[var(--hz-text-2)]",
  erro: "text-[var(--hz-danger)]",
  ok: "text-[var(--hz-ok)]",
  aviso: "text-[var(--hz-warn)]",
};

/** Mensagem de estado de tela (erro, ok, aviso). Sem hex solto. */
export function EstadoMensagem({
  children,
  tom = "neutro",
  className = "",
}: {
  children: ReactNode;
  tom?: Tom;
  className?: string;
}) {
  return (
    <p className={`mb-3 text-[13px] ${tomClasse[tom]} ${className}`.trim()}>
      {children}
    </p>
  );
}
