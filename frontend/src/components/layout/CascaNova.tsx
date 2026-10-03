import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Archive,
  ArrowLeft,
  BarChart2,
  Beaker,
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
import { Logo } from "../brand/Logo";

const ROTULO: Record<string, string> = {
  consultora: "Consultora",
  orgao: "Órgão",
  funcionario: "Funcionário",
  dev: "Desenvolvimento",
};

function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "HZ";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

type Atalho = { rotulo: string; caminho: string; icone: ReactNode; marcado: boolean };

export function CascaNova({ children }: { children: ReactNode }) {
  const { usuario, sair } = useAuth();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const [fixo, setFixo] = useState(false);
  const [sobre, setSobre] = useState(false);
  const aberto = fixo || sobre;
  useEffect(() => {
    localStorage.removeItem("orizon-design-consultora");
  }, []);
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
              marcado: pathname === "/projetos" || pathname === "/projetos/novo",
            },
            {
              rotulo: "Novo trabalho",
              caminho: "/projetos/novo",
              icone: <Plus size={16} />,
              marcado: pathname === "/projetos/novo",
            },
            {
              rotulo: "Pesquisas",
              caminho: "/consultora/pesquisas?aba=pesquisas",
              icone: <ClipboardList size={16} />,
              marcado: pathname.startsWith("/consultora/pesquisas") && aba !== "modelos" && aba !== "organizacao" && !search.includes("tipo=DESEMPENHO"),
            },
            {
              rotulo: "Avaliações",
              caminho: "/consultora/pesquisas?aba=pesquisas&tipo=DESEMPENHO",
              icone: <Star size={16} />,
              marcado: pathname.startsWith("/consultora/pesquisas") && search.includes("tipo=DESEMPENHO"),
            },
            {
              rotulo: "Modelos",
              caminho: "/consultora/pesquisas?aba=modelos",
              icone: <Archive size={16} />,
              marcado: pathname.startsWith("/consultora/pesquisas") && aba === "modelos",
            },
            {
              rotulo: "Organização",
              caminho: "/consultora/pesquisas?aba=organizacao",
              icone: <Users size={16} />,
              marcado: pathname.startsWith("/consultora/pesquisas") && aba === "organizacao",
            },
            ...(usuario?.lab_habilitado
              ? [
                  {
                    rotulo: "Laboratório",
                    caminho: "/lab",
                    icone: <Beaker size={16} />,
                    marcado: pathname.startsWith("/lab"),
                  } satisfies Atalho,
                ]
              : []),
          ]
        : painel === "funcionario"
          ? [
              { rotulo: "Início", caminho: "/inicio", icone: <Home size={16} />, marcado: pathname === "/inicio" && !aba },
              { rotulo: "Pendentes", caminho: "/inicio?aba=pendentes", icone: <ClipboardList size={16} />, marcado: aba === "pendentes" },
              { rotulo: "Em andamento", caminho: "/inicio?aba=andamento", icone: <Clock size={16} />, marcado: aba === "andamento" },
              { rotulo: "Concluídas", caminho: "/inicio?aba=concluidas", icone: <Star size={16} />, marcado: aba === "concluidas" },
            ]
          : painel === "dev"
            ? [
                { rotulo: "Início", caminho: "/inicio", icone: <Home size={16} />, marcado: pathname === "/inicio" && !aba },
                { rotulo: "Saúde", caminho: "/inicio?aba=saude", icone: <BarChart2 size={16} />, marcado: aba === "saude" },
                { rotulo: "Pedidos", caminho: "/inicio?aba=pedidos", icone: <ClipboardList size={16} />, marcado: aba === "pedidos" },
                { rotulo: "Consultoras", caminho: "/inicio?aba=consultores", icone: <Users size={16} />, marcado: aba === "consultores" },
                { rotulo: "E-mail", caminho: "/inicio?aba=email", icone: <Settings size={16} />, marcado: aba === "email" },
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
    <div className="min-h-screen bg-[var(--hz-bg)] text-[var(--hz-text)]">
      <div className="relative min-[900px]:flex">
        <aside
          className={`hidden min-[900px]:flex min-[900px]:h-screen min-[900px]:flex-col min-[900px]:shrink-0 px-2 py-3 ${
            sobre && !fixo ? "absolute z-40" : "sticky top-0 z-30"
          }`}
          style={{
            width: aberto ? 248 : 72,
            background: "var(--hz-sidebar)",
            color: "var(--hz-sidebar-text)",
          }}
          onMouseEnter={() => setSobre(true)}
          onMouseLeave={() => setSobre(false)}
        >
          <button
            type="button"
            className="mb-4 flex items-center gap-2 px-1"
            onClick={() => setFixo((valor) => !valor)}
            aria-label={fixo ? "Recolher menu" : "Fixar menu"}
          >
            <Logo
              variante={aberto ? "horizontal" : "simbolo"}
              tamanho={28}
              tom="escuro"
            />
          </button>
          <nav className="flex flex-col gap-1" aria-label="Principal">
            {atalhos.map((item) => (
              <button
                key={item.caminho}
                type="button"
                title={aberto ? undefined : item.rotulo}
                onClick={() => navigate(item.caminho)}
                className="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[14px]"
                style={{
                  background: item.marcado ? "var(--hz-primary)" : "transparent",
                  color: item.marcado ? "var(--hz-surface)" : "var(--hz-sidebar-text)",
                }}
              >
                {item.icone}
                {aberto ? <span className="truncate">{item.rotulo}</span> : null}
                {aberto && item.marcado ? <span className="ml-auto">›</span> : null}
              </button>
            ))}
          </nav>
          <div className="mt-auto flex items-center gap-2 px-1 pt-4">
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold"
              style={{ background: "var(--hz-sidebar-active)", color: "var(--hz-surface)" }}
            >
              {iniciais(nome)}
            </span>
            {aberto ? (
              <span className="min-w-0">
                <span className="block truncate text-[13px]" style={{ color: "var(--hz-auth-text)" }}>
                  {nome}
                </span>
                <span className="text-[12px]">{papel}</span>
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => void encerrar()}
              className="ml-auto p-2"
              aria-label="Sair"
              title="Sair"
            >
              <LogOut size={16} />
            </button>
          </div>
        </aside>
        <div className="min-w-0 flex-1 pb-28 min-[900px]:pb-10">
          <header className="flex items-center justify-between px-4 pt-4 min-[900px]:hidden">
            <Logo variante="horizontal" tamanho={22} tom="claro" />
            <button type="button" onClick={() => void encerrar()} className="text-[13px]">
              Sair
            </button>
          </header>
          <main className="px-4 pt-4 min-[900px]:px-8 min-[900px]:pt-6">{children}</main>
        </div>
      </div>
      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex gap-1 overflow-x-auto px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] min-[900px]:hidden"
        style={{ background: "var(--hz-sidebar)", color: "var(--hz-sidebar-text)" }}
        aria-label="Atalhos"
      >
        {atalhos.slice(0, 5).map((item) => (
          <button
            key={item.caminho}
            type="button"
            onClick={() => navigate(item.caminho)}
            className="flex min-h-11 shrink-0 flex-col items-center gap-1 px-2 text-[11px]"
            style={{ color: item.marcado ? "var(--hz-surface)" : "var(--hz-sidebar-text)" }}
          >
            {item.icone}
            {item.rotulo}
          </button>
        ))}
      </nav>
    </div>
  );
}
