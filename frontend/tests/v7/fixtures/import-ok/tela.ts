import type { FonteDeDados } from "./FonteDeDados";

export function Tela(fonte: FonteDeDados) {
  return fonte.ler("01").nota;
}
