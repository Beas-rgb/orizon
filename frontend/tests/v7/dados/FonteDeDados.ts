import type { LeituraDeTela } from "./contratos";

export interface FonteDeDados {
  ler(tela: string): LeituraDeTela;
}
