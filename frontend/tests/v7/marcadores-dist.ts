import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

export const PREFIXO_MARCADOR = "__HZ_V7_";

/**
 * No PR 0 a lista fica vazia: nenhum marcador pode aparecer no dist.
 * No PR 12 ela pode passar a incluir "98", "99" e "100".
 * As telas 101 a 106 continuam barradas.
 */
export const TELAS_PERMITIDAS_NO_DIST: readonly string[] = [];

export function marcadoresProibidos(texto: string): string[] {
  const todos = texto.match(/__HZ_V7_[A-Za-z0-9_]+/g) ?? [];
  return todos.filter((marca) => {
    const tela = /^__HZ_V7_(\d{2,3})__$/.exec(marca)?.[1];
    return !(tela !== undefined && TELAS_PERMITIDAS_NO_DIST.includes(tela));
  });
}

export function procurarMarcadores(dir: string): { arquivo: string; marcas: string[] }[] {
  const achados: { arquivo: string; marcas: string[] }[] = [];
  const visitar = (atual: string) => {
    for (const nome of readdirSync(atual)) {
      const caminho = path.join(atual, nome);
      const info = statSync(caminho);
      if (info.isDirectory()) {
        visitar(caminho);
        continue;
      }
      const marcas = marcadoresProibidos(readFileSync(caminho, "utf8"));
      if (marcas.length) {
        achados.push({ arquivo: path.relative(dir, caminho).replaceAll("\\", "/"), marcas });
      }
    }
  };
  visitar(dir);
  return achados;
}
