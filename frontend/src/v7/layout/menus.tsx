import type { ReactNode } from "react";
import {
  Archive, ArrowLeft, BarChart3, BookOpen, Briefcase, CheckCircle2, ClipboardList, FileText, FlaskConical, Home, Layers, Mail, Network, Plus, Send, Server, Settings, Star, Users, Bell, History,
} from "lucide-react";

export type ItemMenu = { id: string; rotulo: string; para: string; icone: ReactNode; cont?: number; grupo?: string; baixo?: boolean };
/** Perfis de interface. "trabalho" = consultora dentro de um trabalho (menu do painel do trabalho). */
export type Perfil = "ti" | "consultora" | "trabalho" | "orgao" | "servidor";

/** Rotas reais do produto (registro.tsx / plano, seção 7). A vitrine /v7/tela/NN fica no PR 11. */

/**
 * Menus por perfil (v7).
 * - Painel geral da consultora ≠ painel do trabalho (menu próprio, com "Voltar aos trabalhos").
 * - Organização: só no trabalho (consultora) e no órgão quando a chave está ligada. Servidor nunca vê.
 */
export function menuDe(perfil: Perfil, opcoes: { orgaoVeOrganizacao?: boolean; trabalhoId?: string } = {}): ItemMenu[] {
  const id = opcoes.trabalhoId;
  const trab = (aba?: string) => (id ? `/projetos/${id}${aba ? `?aba=${aba}` : ""}` : "/inicio");
  switch (perfil) {
    case "ti":
      return [
        { id: "inicio", rotulo: "Visão geral", para: "/inicio", icone: <Home />, baixo: true },
        { id: "saude", rotulo: "Saúde", para: "/inicio?aba=saude", icone: <Server />, baixo: true },
        { id: "pedidos", rotulo: "Pedidos de consultora", para: "/inicio?aba=pedidos", icone: <ClipboardList />, cont: 3, baixo: true },
        { id: "consultoras", rotulo: "Consultoras", para: "/inicio?aba=consultores", icone: <Users /> },
        { id: "email", rotulo: "Diagnóstico de e-mail", para: "/inicio?aba=email", icone: <Mail /> },
      ];
    case "consultora":
      return [
        { id: "trabalhos", rotulo: "Trabalhos", para: "/inicio", icone: <Briefcase />, cont: 4, grupo: "Principal", baixo: true },
        { id: "novo", rotulo: "Novo trabalho", para: "/projetos/novo", icone: <Plus /> },
        { id: "pesquisas", rotulo: "Pesquisas", para: "/consultora/pesquisas", icone: <ClipboardList />, cont: 14, baixo: true },
        { id: "avaliacoes", rotulo: "Avaliações", para: "/consultora/pesquisas?tipo=DESEMPENHO", icone: <Star /> },
        { id: "modelos", rotulo: "Modelos", para: "/consultora/pesquisas?aba=modelos", icone: <Layers /> },
        { id: "banco", rotulo: "Banco de perguntas", para: "/banco-perguntas", icone: <BookOpen />, grupo: "Acervo" },
        { id: "biblioteca", rotulo: "Biblioteca", para: "/biblioteca", icone: <Archive />, baixo: true },
        { id: "lab", rotulo: "Laboratório", para: "/lab", icone: <FlaskConical /> },
        { id: "avisos", rotulo: "Notificações", para: "/notificacoes", icone: <Bell />, cont: 2, grupo: "Conta" },
        { id: "conta", rotulo: "Minha conta", para: "/conta", icone: <Settings /> },
      ];
    case "trabalho":
      return [
        { id: "inicio", rotulo: "Início do trabalho", para: trab(), icone: <Home />, grupo: "VALEPREV", baixo: true },
        { id: "pesquisas", rotulo: "Pesquisas", para: trab("pesquisas"), icone: <ClipboardList /> },
        { id: "modelos", rotulo: "Modelos", para: "/consultora/pesquisas?aba=modelos", icone: <Layers /> },
        { id: "dashboard", rotulo: "Dashboard", para: trab("dashboard"), icone: <BarChart3 />, baixo: true },
        { id: "organizacao", rotulo: "Organização", para: trab("organizacao"), icone: <Network />, baixo: true },
        { id: "participantes", rotulo: "Participantes", para: trab("participantes"), icone: <Users />, grupo: "Gestão" },
        { id: "biblioteca", rotulo: "Biblioteca", para: trab("biblioteca"), icone: <Archive /> },
        { id: "entregas", rotulo: "Entregas de e-mail", para: trab("entregas"), icone: <Send /> },
        { id: "historico", rotulo: "Histórico", para: trab("historico"), icone: <History /> },
        { id: "config", rotulo: "Configurações", para: trab("config"), icone: <Settings /> },
        { id: "voltar", rotulo: "Voltar aos trabalhos", para: "/inicio", icone: <ArrowLeft /> },
      ];
    case "orgao":
      return [
        { id: "inicio", rotulo: "Painel", para: "/inicio", icone: <Home />, baixo: true },
        { id: "trabalhos", rotulo: "Meus trabalhos", para: "/inicio?aba=trabalhos", icone: <Briefcase /> },
        { id: "resultados", rotulo: "Consolidado", para: "/inicio?aba=consolidado", icone: <BarChart3 />, baixo: true },
        ...(opcoes.orgaoVeOrganizacao ? [{ id: "organizacao", rotulo: "Organização", para: "/inicio?aba=organizacao", icone: <Network /> }] : []),
        { id: "documentos", rotulo: "Documentos", para: "/documentos", icone: <FileText />, baixo: true },
      ];
    case "servidor":
      return [
        { id: "inicio", rotulo: "Início", para: "/inicio", icone: <Home />, grupo: "Minhas pesquisas", baixo: true },
        { id: "concluidas", rotulo: "Concluídas", para: "/inicio?aba=concluidas", icone: <CheckCircle2 />, cont: 3 },
        { id: "avaliar", rotulo: "Avaliar colegas", para: "/inicio?aba=avaliar", icone: <Users />, cont: 2, grupo: "Desempenho", baixo: true },
        { id: "notas", rotulo: "Minhas notas", para: "/minhas-notas", icone: <Star />, baixo: true },
        { id: "documentos", rotulo: "Documentos", para: "/documentos", icone: <FileText />, grupo: "Trabalho" },
      ];
  }
}
