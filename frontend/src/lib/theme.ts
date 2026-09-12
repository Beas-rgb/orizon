import type { CSSProperties } from "react";

export const ACCENT = "#1D5FAF";
export const ACCENT_DARK = "#164A8A";

export const glassStyle: CSSProperties = {
  background: "rgba(255,255,255,0.45)",
  backdropFilter: "blur(28px) saturate(160%)",
  WebkitBackdropFilter: "blur(28px) saturate(160%)",
  border: "1px solid rgba(255,255,255,0.6)",
  boxShadow: "0 6px 24px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.75)",
};

export const dropdownStyle: CSSProperties = {
  background: "rgba(244,247,252,0.92)",
  backdropFilter: "blur(30px) saturate(180%)",
  WebkitBackdropFilter: "blur(30px) saturate(180%)",
  border: "1px solid rgba(255,255,255,0.75)",
  boxShadow: "0 16px 40px rgba(0,0,0,0.14)",
};

export function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "OR";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[1][0]).toUpperCase();
}
