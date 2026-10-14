/** Regras de exibição v7 (compartilhadas). */
export const ANONIMATO_MINIMO = 5;

export type Faixa = "forte" | "atencao" | "critico";
/** ≥75 Forte · 50–74 Atenção · <50 Crítico */
export function faixa(nota: number): Faixa {
  if (nota >= 75) return "forte";
  if (nota >= 50) return "atencao";
  return "critico";
}
export const ROTULO_FAIXA: Record<Faixa, string> = { forte: "Forte", atencao: "Atenção", critico: "Crítico" };


/** Nota final = média ponderada dos grupos com nota (pesos em %). Grupos sem nota (ex.: subordinados < 5) não entram. */
export function mediaPonderada(grupos: { peso: number; nota: number | null }[]): number | null {
  const validos = grupos.filter((g) => g.nota !== null && g.peso > 0);
  const soma = validos.reduce((s, g) => s + g.peso, 0);
  if (!soma) return null;
  return Math.round(validos.reduce((s, g) => s + (g.nota as number) * g.peso, 0) / soma);
}
