/** Infraestrutura. Passa a valer sobre as telas a partir do PR A ou do PR 1. */
export const LIMITES = {
  jsInicialGzipKb: 120,
  rotaGzipKb: 40,
  cssGzipKb: 30,
  pesosInterMax: 4,
  performanceMin: 90,
  acessibilidadeMin: 95,
  clsMax: 0.05,
  tarefaLongaMs: 200,
} as const;

export type RelatorioDesempenho = {
  jsInicialGzipKb: number;
  rotaGzipKb: number;
  cssGzipKb: number;
  pesosInter: number;
  performance: number;
  acessibilidade: number;
  cls: number;
  tarefaLongaMs: number;
};

export function avaliarDesempenho(relatorio: RelatorioDesempenho): string[] {
  const erros: string[] = [];
  if (relatorio.jsInicialGzipKb > LIMITES.jsInicialGzipKb) erros.push("js inicial");
  if (relatorio.rotaGzipKb > LIMITES.rotaGzipKb) erros.push("rota");
  if (relatorio.cssGzipKb > LIMITES.cssGzipKb) erros.push("css");
  if (relatorio.pesosInter > LIMITES.pesosInterMax) erros.push("inter");
  if (relatorio.performance < LIMITES.performanceMin) erros.push("performance");
  if (relatorio.acessibilidade < LIMITES.acessibilidadeMin) erros.push("acessibilidade");
  if (relatorio.cls > LIMITES.clsMax) erros.push("cls");
  if (relatorio.tarefaLongaMs > LIMITES.tarefaLongaMs) erros.push("tarefa longa");
  return erros;
}

export function relatorioNoLimite(): RelatorioDesempenho {
  return {
    jsInicialGzipKb: LIMITES.jsInicialGzipKb,
    rotaGzipKb: LIMITES.rotaGzipKb,
    cssGzipKb: LIMITES.cssGzipKb,
    pesosInter: LIMITES.pesosInterMax,
    performance: LIMITES.performanceMin,
    acessibilidade: LIMITES.acessibilidadeMin,
    cls: LIMITES.clsMax,
    tarefaLongaMs: LIMITES.tarefaLongaMs,
  };
}
