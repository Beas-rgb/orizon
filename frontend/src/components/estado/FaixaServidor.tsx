import { AvisoAcordando } from "./AvisoAcordando";
import { useServidor } from "../../lib/servidor";

export function FaixaServidor() {
  const { estado, tentarDeNovo } = useServidor();
  if (estado !== "acordando" && estado !== "falha") return null;
  return <AvisoAcordando onTentar={estado === "falha" ? tentarDeNovo : undefined} />;
}
