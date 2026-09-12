import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
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
  const nome = usuario?.nome || "Usuário";
  const painel = usuario?.painel || "";
  const label = papelRotulo[painel] || "Horizon";

  const sections =
    painel === "consultora"
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
                label: "Pesquisas",
                active: active === "pesquisas",
                onClick: () => navigate("/projetos"),
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
              title: "Principal",
              items: [
                {
                  icon: iconMap.LayoutDashboard,
                  label: "Meus trabalhos",
                  active: active === "dashboard",
                  onClick: () => navigate("/inicio"),
                },
                {
                  icon: iconMap.BarChart2,
                  label: "Resultados",
                  active: active === "resultados",
                  onClick: () => navigate("/inicio"),
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
                    icon: iconMap.LayoutDashboard,
                    label: "Início",
                    active: active === "dashboard",
                    onClick: () => navigate("/inicio"),
                  },
                  {
                    icon: iconMap.ClipboardList,
                    label: "Responder",
                    active: active === "responder",
                    onClick: () => navigate("/responder"),
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
      />
      <Navbar
        nome={nome}
        papelLabel={label}
        onMenuClick={() => setSidebarOpen((v) => !v)}
        onSair={() => void sair().then(() => navigate("/entrar"))}
        searchHints={searchHints}
      />

      <main className="relative z-10 pt-[76px] px-4 sm:px-6 pb-8 max-w-[1440px] mx-auto w-full">
        {children}
      </main>
    </div>
  );
}
