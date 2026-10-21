import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "./Carregamento";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** "primario" = o único botão azul da tela. */
  tipo?: "primario" | "escuro" | "secundario" | "fantasma";
  icone?: ReactNode;
  ocupado?: boolean;
  textoOcupado?: string;
};

export function Botao({ tipo = "secundario", icone, ocupado, textoOcupado, children, className, disabled, ...resto }: Props) {
  const classe = ["v7-btn", tipo === "secundario" ? "" : tipo, className].filter(Boolean).join(" ");
  return (
    <button type="button" className={classe} disabled={disabled || ocupado} aria-busy={ocupado || undefined} {...resto}>
      {ocupado ? <Spinner /> : icone}
      {ocupado && textoOcupado ? textoOcupado : children}
    </button>
  );
}
