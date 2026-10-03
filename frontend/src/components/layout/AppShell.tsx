import type { ReactNode } from "react";
import { useAuth } from "../../auth/AuthContext";
import { AvisoAcordando } from "../estado/AvisoAcordando";
import { CascaNova } from "./CascaNova";

type Props = {
  children: ReactNode;
  active?: string;
  searchHints?: { type: string; label: string; icon: string }[];
};

export function AppShell({ children }: Props) {
  const { conexao } = useAuth();
  return (
    <CascaNova>
      {conexao === "instavel" ? <AvisoAcordando /> : null}
      {children}
    </CascaNova>
  );
}
