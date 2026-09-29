import { useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Archive,
  ArrowLeft,
  BarChart2,
  Briefcase,
  ClipboardList,
  Clock,
  Home,
  LogOut,
  Plus,
  Settings,
  Star,
  Users,
} from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { InterruptorDesign } from "./InterruptorDesign";

const ROTULO: Record<string, string> = {
  consultora: "Consultora",
  orgao: "Órgão",
  funcionario: "Funcionário",
  dev: "Desenvolvimento",
};

function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "OR";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

type Atalho = { rotulo: string; caminho: string; icone: ReactNode; marcado: boolean };

export function CascaNova({ children }: { children: ReactNode }) {
  const { usuario, sair } = useAuth();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const [menuAberto, setMenuAberto] = useState(true);
  const nome = usuario?.nome || "Usuário";
  const painel = usuario?.painel || "";
  const papel = ROTULO[painel] || "Horizon";
  const partes = pathname.split("/").filter(Boolean);
  const trabalhoId =
    partes[0] === "projetos" && partes[1] && partes[1] !== "novo" ? partes[1] : null;
  const aba = new URLSearchParams(search).get("aba") || "";

  const atalhos: Atalho[] = trabalhoId
    ? [
        { rotulo: "Início", caminho: "/inicio", icone: <Home size={16} />, marcado: false },
        {
          rotulo: "Visão geral",
          caminho: `/projetos/${trabalhoId}?aba=visao`,
          icone: <Briefcase size={16} />,
          marcado: aba === "" || aba === "visao",
        },
        {
          rotulo: "Estrutura",
          caminho: `/projetos/${trabalhoId}?aba=estrutura`,
          icone: <Star size={16} />,
          marcado: aba === "estrutura",
        },
        {
          rotulo: "Participantes",
          caminho: `/projetos/${trabalhoId}?aba=participantes`,
          icone: <Users size={16} />,
          marcado: aba === "participantes",
        },
        {
          rotulo: "Pesquisas",
          caminho: `/projetos/${trabalhoId}?aba=pesquisas`,
          icone: <ClipboardList size={16} />,
          marcado: aba === "pesquisas" || partes[2] === "pesquisas",
        },
        {
          rotulo: "Resultados",
          caminho: `/projetos/${trabalhoId}?aba=resultados`,
          icone: <BarChart2 size={16} />,
          marcado: aba === "resultados",
        },
        {
          rotulo: "Histórico",
          caminho: `/projetos/${trabalhoId}?aba=historico`,
          icone: <Clock size={16} />,
          marcado: aba === "historico",
        },
        {
          rotulo: "Biblioteca",
          caminho: `/projetos/${trabalhoId}?aba=biblioteca`,
          icone: <Archive size={16} />,
          marcado: aba === "biblioteca",
        },
        {
          rotulo: "Configurações",
          caminho: `/projetos/${trabalhoId}?aba=config`,
          icone: <Settings size={16} />,
          marcado: aba === "config",
        },
        {
          rotulo: "Voltar aos trabalhos",
          caminho: "/projetos",
          icone: <ArrowLeft size={16} />,
          marcado: false,
        },
      ]
    : painel === "orgao"
      ? [
          { rotulo: "Início", caminho: "/inicio", icone: <Home size={16} />, marcado: aba === "" },
          {
            rotulo: "Meus trabalhos",
            caminho: "/inicio?aba=trabalhos",
            icone: <Briefcase size={16} />,
            marcado: aba === "trabalhos",
          },
          {
            rotulo: "Ativas",
            caminho: "/inicio?aba=ativas",
            icone: <ClipboardList size={16} />,
            marcado: aba === "ativas",
          },
          {
            rotulo: "Agendadas",
            caminho: "/inicio?aba=agendadas",
            icone: <Clock size={16} />,
            marcado: aba === "agendadas",
          },
          {
            rotulo: "Encerradas",
            caminho: "/inicio?aba=encerradas",
            icone: <Archive size={16} />,
            marcado: aba === "encerradas",
          },
          {
            rotulo: "Histórico",
            caminho: "/inicio?aba=historico",
            icone: <BarChart2 size={16} />,
            marcado: aba === "historico",
          },
        ]
      : painel === "consultora"
        ? [
            {
              rotulo: "Início",
              caminho: "/inicio",
              icone: <Home size={16} />,
              marcado: pathname === "/inicio",
            },
            {
              rotulo: "Trabalhos",
              caminho: "/projetos",
              icone: <Briefcase size={16} />,
              marcado: pathname === "/projetos",
            },
            {
              rotulo: "Novo trabalho",
              caminho: "/projetos/novo",
              icone: <Plus size={16} />,
              marcado: pathname === "/projetos/novo",
            },
            {
              rotulo: "Pesquisas",
              caminho: "/consultora/pesquisas",
              icone: <ClipboardList size={16} />,
              marcado: pathname.startsWith("/consultora/pesquisas"),
            },
          ]
        : [
            {
              rotulo: "Início",
              caminho: "/inicio",
              icone: <Home size={16} />,
              marcado: pathname === "/inicio",
            },
          ];

  async function encerrar() {
    await sair();
    navigate("/entrar");
  }

  return (
    <div className="min-h-screen bg-[#f4f3ef] text-[#1c1c1c]">
      <div className="min-[900px]:flex">
        <aside
          className={`hidden min-[900px]:flex min-[900px]:flex-col min-[900px]:sticky min-[900px]:top-0 min-[900px]:h-screen min-[900px]:shrink-0 border-r border-black/[0.06] bg-[#f7f6f3] px-3 py-4 ${
            menuAberto ? "w-[248px]" : "w-[76px]"
          }`}
        >
          <div className="flex items-center gap-2 px-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#171717] text-[12px] font-semibold text-white">
              O
            </span>
            {menuAberto ? (
              <span>
                <span className="block text-[15px] font-semibold leading-none">Orizon</span>
                <span className="text-[10px] tracking-[0.14em] text-[#8a8a8a]">
                  {papel.toUpperCase()}
                </span>
              </span>
            ) : null}
          </div>
          <nav className="mt-6 flex flex-col gap-1" aria-label="Principal">
            {atalhos.map((item) => (
              <button
                key={item.caminho}
                type="button"
                onClick={() => navigate(item.caminho)}
                className={`flex items-center gap-2 rounded-xl px-3 py-2 text-left text-[14px] ${
                  item.marcado
                    ? "border-l-2 border-[#171717] bg-[#f3f2ee] font-semibold text-[#171717]"
                    : "border-l-2 border-transparent text-[#3a3a3a]"
                }`}
              >
                {item.icone}
                {menuAberto ? item.rotulo : null}
              </button>
            ))}
          </nav>
          <div className="mt-auto flex items-center gap-2 px-2 pt-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#171717] text-[12px] font-semibold text-white">
              {iniciais(nome)}
            </span>
            {menuAberto ? (
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-semibold">{nome}</span>
                <span className="text-[12px] text-[#6d6d6d]">{papel}</span>
              </span>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => void encerrar()}
            className="mt-2 flex items-center gap-2 px-3 py-2 text-left text-[13px] text-[#6d6d6d]"
          >
            <LogOut size={14} />
            {menuAberto ? "Sair" : null}
          </button>
          <button
            type="button"
            onClick={() => setMenuAberto((aberto) => !aberto)}
            className="px-3 py-2 text-left text-[12px] text-[#8a8a8a]"
          >
            {menuAberto ? "Recolher menu" : "Abrir"}
          </button>
        </aside>
        <div className="min-w-0 flex-1 pb-28 min-[900px]:pb-10">
          <header className="flex items-center justify-between px-4 pt-4 min-[900px]:hidden">
            <span className="flex items-center gap-2 font-semibold">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#171717] text-[12px] text-white">
                O
              </span>
              Orizon
            </span>
            <button type="button" onClick={() => void encerrar()} className="text-[13px] font-medium text-[#6d6d6d]">
              Sair
            </button>
          </header>
          <main className="px-4 pt-4 min-[900px]:px-8 min-[900px]:pt-6">{children}</main>
        </div>
      </div>
      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex gap-1 overflow-x-auto border-t border-black/[0.06] bg-[#f7f6f3] px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] min-[900px]:hidden"
        aria-label="Atalhos"
      >
        {atalhos.map((item) => (
          <button
            key={item.caminho}
            type="button"
            onClick={() => navigate(item.caminho)}
            className={`flex shrink-0 flex-col items-center gap-1 px-2 text-[11px] ${
              item.marcado ? "font-semibold text-[#171717]" : "text-[#8a8a8a]"
            }`}
          >
            {item.icone}
            {item.rotulo}
          </button>
        ))}
      </nav>
      <InterruptorDesign />
    </div>
  );
}
