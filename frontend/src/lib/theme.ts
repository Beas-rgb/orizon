import type { CSSProperties } from "react";

export const ACCENT = "var(--hz-accent)";
export const ACCENT_DARK = "var(--hz-accent-dark)";

export const glassStyle: CSSProperties = {
  background: "var(--hz-surface)",
  border: "1px solid var(--hz-black-06)",
  boxShadow: "0 1px 2px var(--hz-black-04)",
};

export const dropdownStyle: CSSProperties = {
  background: "var(--hz-mist-92)",
  backdropFilter: "blur(30px) saturate(180%)",
  WebkitBackdropFilter: "blur(30px) saturate(180%)",
  border: "1px solid var(--hz-white-75)",
  boxShadow: "0 16px 40px var(--hz-black-14)",
};

export function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "OR";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[1][0]).toUpperCase();
}
