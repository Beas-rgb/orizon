/** Infraestrutura. Passa a valer sobre as telas a partir do PR A ou do PR 1. */
export const LARGURAS_PX = [759, 760, 761, 768, 1023, 1024, 1025] as const;

/** Corte aprovado em 16/10 às 20:20: até 1023 é celular; 1024 em diante é desktop. */
export const CORTE_DESKTOP_PX = 1024;

export const TOQUE_MIN_PX = 44;

export type MedidaLargura = {
  largura: number;
  rolagemLateral: boolean;
  textoCortado: boolean;
  menorAlvoPx: number;
};

export function layoutDe(largura: number): "celular" | "desktop" {
  return largura >= CORTE_DESKTOP_PX ? "desktop" : "celular";
}

export function avaliarMedida(medida: MedidaLargura): string[] {
  const erros: string[] = [];
  if (!(LARGURAS_PX as readonly number[]).includes(medida.largura)) erros.push("largura fora da matriz");
  if (medida.rolagemLateral) erros.push("rolagem lateral");
  if (medida.textoCortado) erros.push("texto cortado");
  if (medida.menorAlvoPx < TOQUE_MIN_PX) erros.push("toque menor que 44 px");
  return erros;
}
