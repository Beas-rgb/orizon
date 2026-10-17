import "../../styles/v7.css";
import { LogoHorizon } from "../../v7/ui/LogoHorizon";

type Variante = "simbolo" | "horizontal" | "empilhado";
type Tom = "claro" | "escuro";

type Props = {
  variante?: Variante;
  tamanho?: number;
  tom?: Tom;
};

/** A marca é o PNG único. Trocar o arquivo troca a logo em todas as telas que usam este componente. */
export function Logo({ variante = "simbolo", tamanho = 48 }: Props) {
  return <LogoHorizon palavra={variante !== "simbolo"} altura={tamanho} />;
}
