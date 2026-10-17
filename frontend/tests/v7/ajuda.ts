import path from "node:path";
import { varrer } from "../../scripts/v7/varredura.mjs";

export const raizFront = process.cwd();
export const pastaFixtures = path.join(process.cwd(), "tests/v7/fixtures");

export function regrasDe(relativo: string) {
  const resultado = varrer(path.join(pastaFixtures, relativo));
  return resultado;
}
