import { useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Briefcase,
  ClipboardList,
  Home,
  LogOut,
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

type Atalho = { rotulo: string; caminho: string; icone: ReactNode };

export function CascaNova({ children }: { children: ReactNode }) {
  const { usuario, sair } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [menuAberto, setMenuAberto] = useState(true);
  const nome = usuario?.nome || "Usuário";
  const painel = usuario?.painel || "";
  const papel = ROTULO[painel] || "Horizon";

  const atalhos: Atalho[] = [{ rotulo: "Início", caminho: "/inicio", icone: <Home size={16} /> }];
  if (painel === "consultora") {
    atalhos.push(
      { rotulo: "Trabalhos", caminho: "/projetos", icone: <Briefcase size={16} /> },
      { rotulo: "Pesquisas", caminho: "/consultora/pesquisas", icone: <ClipboardList size={16} /> },
    );
  }

  function ativo(caminho: string) {
    if (caminho === "/inicio") return pathname === "/inicio";
    return pathname === caminho || pathname.startsWith(`${caminho}/`);
  }

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
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1A3F8F] text-[12px] font-semibold text-white">
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
                  ativo(item.caminho)
                    ? "border-l-2 border-[#1A3F8F] bg-[#E6EDF8] font-semibold text-[#1A3F8F]"
                    : "border-l-2 border-transparent text-[#3a3a3a]"
                }`}
              >
                {item.icone}
                {menuAberto ? item.rotulo : null}
              </button>
            ))}
          </nav>
          <div className="mt-auto flex items-center gap-2 px-2 pt-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#1A3F8F] text-[12px] font-semibold text-white">
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
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1A3F8F] text-[12px] text-white">
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
        className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-black/[0.06] bg-[#f7f6f3] px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] min-[900px]:hidden"
        aria-label="Atalhos"
      >
        {atalhos.map((item) => (
          <button
            key={item.caminho}
            type="button"
            onClick={() => navigate(item.caminho)}
            className={`flex min-w-0 flex-col items-center gap-1 px-2 text-[11px] ${
              ativo(item.caminho) ? "font-semibold text-[#1A3F8F]" : "text-[#8a8a8a]"
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
