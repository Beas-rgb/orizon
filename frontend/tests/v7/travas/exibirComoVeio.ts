import type { LeituraDeTela } from "../dados/contratos";

/** Desenha o JSON como veio. Não recalcula nota, oculto nem desabilitado. */
export function exibirComoVeio(dado: LeituraDeTela): LeituraDeTela {
  return {
    nota: dado.nota,
    oculto: dado.oculto,
    desabilitado: dado.desabilitado,
  };
}
