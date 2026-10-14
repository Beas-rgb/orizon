import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { AppShellV7 } from "../../v7/layout/AppShellV7";
import type { Perfil } from "../../v7/layout/menus";

const ROTULO: Record<string, string> = {
  consultora: "Consultora",
  orgao: "Órgão",
  funcionario: "Funcionário",
  dev: "Desenvolvimento",
};

function perfilDe(painel: string, trabalhoId: string | null): Perfil {
  if (trabalhoId && painel === "consultora") return "trabalho";
  if (painel === "dev") return "ti";
  if (painel === "funcionario") return "servidor";
  if (painel === "orgao") return "orgao";
  return "consultora";
}

function ativoDe(perfil: Perfil, pathname: string, aba: string, search: string): string {
  if (perfil === "trabalho") {
    if (pathname.includes("/pesquisas/") || aba === "pesquisas") return "pesquisas";
    if (aba === "dashboard" || aba === "resultados") return "dashboard";
    if (aba === "organizacao" || aba === "estrutura") return "organizacao";
    if (aba === "participantes") return "participantes";
    if (aba === "biblioteca") return "biblioteca";
    if (aba === "entregas") return "entregas";
    if (aba === "historico") return "historico";
    if (aba === "config") return "config";
    return "inicio";
  }
  if (perfil === "ti") {
    if (aba === "saude" || aba === "pedidos" || aba === "email") return aba;
    if (aba === "consultores") return "consultoras";
    return "inicio";
  }
  if (perfil === "orgao") {
    if (aba === "trabalhos") return "trabalhos";
    if (aba === "consolidado") return "resultados";
    if (aba === "organizacao") return "organizacao";
    if (pathname === "/documentos") return "documentos";
    return "inicio";
  }
  if (perfil === "servidor") {
    if (aba === "concluidas") return "concluidas";
    if (aba === "avaliar") return "avaliar";
    if (pathname === "/minhas-notas") return "notas";
    if (pathname === "/documentos") return "documentos";
    return "inicio";
  }
  if (pathname === "/projetos/novo") return "novo";
  if (pathname === "/banco-perguntas") return "banco";
  if (pathname === "/biblioteca") return "biblioteca";
  if (pathname.startsWith("/lab")) return "lab";
  if (pathname === "/notificacoes") return "avisos";
  if (pathname === "/conta") return "conta";
  if (pathname.startsWith("/consultora/pesquisas")) {
    if (aba === "modelos") return "modelos";
    if (search.includes("tipo=DESEMPENHO")) return "avaliacoes";
    return "pesquisas";
  }
  return "trabalhos";
}

export function CascaNova({ children }: { children: ReactNode }) {
  const { usuario, sair } = useAuth();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const nome = usuario?.nome || "Usuário";
  const painel = usuario?.painel || "";
  const papel = ROTULO[painel] || "Horizon";
  const partes = pathname.split("/").filter(Boolean);
  const trabalhoId =
    partes[0] === "projetos" && partes[1] && partes[1] !== "novo" ? partes[1] : null;
  const aba = new URLSearchParams(search).get("aba") || "";
  const perfil = perfilDe(painel, trabalhoId);

  async function encerrar() {
    await sair();
    navigate("/entrar");
  }

  return (
    <AppShellV7
      perfil={perfil}
      ativo={ativoDe(perfil, pathname, aba, search)}
      nome={nome}
      papel={papel}
      trabalhoId={trabalhoId ?? undefined}
      onSair={() => void encerrar()}
    >
      {children}
    </AppShellV7>
  );
}
