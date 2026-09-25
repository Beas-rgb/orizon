import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Navbar } from "./Navbar";
import { Sidebar, iconMap } from "./Sidebar";

type Props = {
  children: ReactNode;
  active?: string;
  searchHints?: { type: string; label: string; icon: string }[];
};

const papelRotulo: Record<string, string> = {
  consultora: "Consultora",
  orgao: "Órgão",
  funcionario: "Funcionário",
  dev: "Desenvolvimento",
};

export function AppShell({ children, active = "dashboard", searchHints }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { usuario, sair } = useAuth();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const nome = usuario?.nome || "Usuário";
  const painel = usuario?.painel || "";
  const label = papelRotulo[painel] || "Horizon";
  const partes = pathname.split("/").filter(Boolean);
  const trabalhoId =
    partes[0] === "projetos" && partes[1] && partes[1] !== "novo" ? partes[1] : null;
  const abaAtual = new URLSearchParams(search).get("aba") || "";

  useEffect(() => {
    if (trabalhoId || (painel === "orgao" && abaAtual)) setSidebarOpen(true);
  }, [trabalhoId, painel, abaAtual]);

  const irTrabalho = (aba: string) => {
    if (!trabalhoId) return;
    navigate(`/projetos/${trabalhoId}?aba=${aba}`);
  };

  const sections = trabalhoId
    ? [
        {
          title: "Trabalho",
          items: [
            {
              icon: iconMap.LayoutDashboard,
              label: "Home",
              onClick: () => navigate("/inicio"),
            },
            {
              icon: iconMap.Briefcase,
              label: "Visão geral",
              active: abaAtual === "" || abaAtual === "visao",
              onClick: () => irTrabalho("visao"),
            },
            {
              icon: iconMap.Star,
              label: "Estrutura",
              active: abaAtual === "estrutura",
              onClick: () => irTrabalho("estrutura"),
            },
            {
              icon: iconMap.Users,
              label: "Participantes",
              active: abaAtual === "participantes",
              onClick: () => irTrabalho("participantes"),
            },
            {
              icon: iconMap.ClipboardList,
              label: "Pesquisas",
              active: abaAtual === "pesquisas" || partes[2] === "pesquisas",
              onClick: () => irTrabalho("pesquisas"),
            },
            {
              icon: iconMap.BarChart2,
              label: "Resultados",
              active: abaAtual === "resultados",
              onClick: () => irTrabalho("resultados"),
            },
            {
              icon: iconMap.Clock,
              label: "Histórico",
              active: abaAtual === "historico",
              onClick: () => irTrabalho("historico"),
            },
            {
              icon: iconMap.Archive,
              label: "Biblioteca",
              active: abaAtual === "biblioteca",
              onClick: () => irTrabalho("biblioteca"),
            },
            {
              icon: iconMap.Settings,
              label: "Configurações",
              active: abaAtual === "config",
              onClick: () => irTrabalho("config"),
            },
          ],
        },
      ]
    : painel === "consultora"
      ? [
          {
            title: "Principal",
            items: [
              {
                icon: iconMap.LayoutDashboard,
                label: "Dashboard",
                active: active === "dashboard",
                onClick: () => navigate("/inicio"),
              },
              {
                icon: iconMap.Briefcase,
                label: "Trabalhos",
                active: active === "projetos",
                onClick: () => navigate("/projetos"),
              },
              {
                icon: iconMap.ClipboardList,
                label: "Novo projeto",
                active: active === "novo",
                onClick: () => navigate("/projetos/novo"),
              },
            ],
          },
          {
            title: "Consultoria",
            items: [
              {
                icon: iconMap.Users,
                label: "Equipe / convites",
                active: active === "equipe",
                onClick: () => navigate("/projetos"),
              },
              {
                icon: iconMap.FileText,
                label: "Pesquisas e Avaliações",
                active: active === "pesquisas",
                onClick: () => navigate("/consultora/pesquisas"),
              },
              {
                icon: iconMap.Archive,
                label: "Biblioteca",
                active: active === "biblioteca",
                onClick: () => navigate("/projetos"),
              },
            ],
          },
        ]
      : painel === "orgao"
        ? [
            {
              title: "Órgão",
              items: [
                {
                  icon: iconMap.LayoutDashboard,
                  label: "Home",
                  active: !abaAtual,
                  onClick: () => navigate("/inicio"),
                },
                {
                  icon: iconMap.Briefcase,
                  label: "Meus trabalhos",
                  active: abaAtual === "trabalhos",
                  onClick: () => navigate("/inicio?aba=trabalhos"),
                },
                {
                  icon: iconMap.ClipboardList,
                  label: "Ativas",
                  active: abaAtual === "ativas",
                  onClick: () => navigate("/inicio?aba=ativas"),
                },
                {
                  icon: iconMap.Clock,
                  label: "Agendadas",
                  active: abaAtual === "agendadas",
                  onClick: () => navigate("/inicio?aba=agendadas"),
                },
                {
                  icon: iconMap.Archive,
                  label: "Encerradas",
                  active: abaAtual === "encerradas",
                  onClick: () => navigate("/inicio?aba=encerradas"),
                },
                {
                  icon: iconMap.BarChart2,
                  label: "Histórico",
                  active: abaAtual === "historico",
                  onClick: () => navigate("/inicio?aba=historico"),
                },
              ],
            },
          ]
        : painel === "funcionario"
          ? [
              {
                title: "Principal",
                items: [
                  {
                    icon: iconMap.ClipboardList,
                    label: "Minhas pesquisas",
                    active: active === "dashboard",
                    onClick: () => navigate("/inicio"),
                  },
                ],
              },
            ]
          : [
              {
                title: "TI",
                items: [
                  {
                    icon: iconMap.Settings,
                    label: "Diagnóstico",
                    active: active === "dashboard",
                    onClick: () => navigate("/inicio"),
                  },
                ],
              },
            ];

  return (
    <div className="min-h-screen relative overflow-x-hidden page-bg">
      <div
        className="absolute pointer-events-none"
        style={{
          top: "-200px",
          left: "-150px",
          width: "700px",
          height: "700px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(90,110,160,0.08) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div
        className="absolute pointer-events-none"
        style={{
          top: "80px",
          right: "-120px",
          width: "500px",
          height: "500px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(100,110,140,0.06) 0%, transparent 70%)",
          filter: "blur(70px)",
        }}
      />

      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        nome={nome}
        papelLabel={label}
        sections={sections}
        manterAberto={Boolean(trabalhoId) || painel === "orgao"}
      />
      <Navbar
        nome={nome}
        papelLabel={label}
        onMenuClick={() => setSidebarOpen((v) => !v)}
        onSair={() => void sair().then(() => navigate("/entrar"))}
        searchHints={searchHints}
      />

      <main className="relative z-10 pt-[70px] sm:pt-[76px] px-3 sm:px-6 pb-10 sm:pb-8 max-w-[1440px] mx-auto w-full"
        style={{ paddingBottom: "max(2.5rem, env(safe-area-inset-bottom))" }}
      >
        {children}
      </main>
    </div>
  );
}
