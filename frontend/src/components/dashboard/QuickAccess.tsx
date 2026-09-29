import { motion } from "motion/react";
import { ArrowRight, List, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { glassStyle } from "../../lib/theme";

const actions = [
  {
    icon: Plus,
    label: "Novo Trabalho",
    description: "Criar projeto",
    color: "#1D5FAF",
    bg: "rgba(29,95,175,0.10)",
    border: "rgba(29,95,175,0.20)",
    to: "/projetos/novo",
  },
  {
    icon: List,
    label: "Lista de Trabalhos",
    description: "Ver todos",
    color: "#4B5C6E",
    bg: "rgba(75,92,110,0.09)",
    border: "rgba(75,92,110,0.18)",
    to: "/projetos",
  },
];

export function QuickAccess({
  stats,
}: {
  stats: { label: string; value: string; sub: string }[];
}) {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col gap-4 w-full lg:w-60 shrink-0">
      <div className="rounded-3xl p-4" style={glassStyle}>
        <p className="text-gray-800 mb-3 text-[13px] font-bold">Acesso Rápido</p>
        <div className="flex flex-col gap-2">
          {actions.map((action) => (
            <motion.button
              key={action.label}
              type="button"
              whileHover={{ scale: 1.02, x: 2 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate(action.to)}
              className="flex items-center gap-3 p-3 rounded-2xl text-left group"
              style={{ background: action.bg, border: `1px solid ${action.border}` }}
            >
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                style={{
                  background: `${action.color}18`,
                  border: `1px solid ${action.color}28`,
                }}
              >
                <action.icon size={15} style={{ color: action.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] font-semibold text-gray-800">{action.label}</p>
                <p className="text-[10px] text-gray-400">{action.description}</p>
              </div>
              <ArrowRight
                size={12}
                className="opacity-0 group-hover:opacity-70"
                style={{ color: action.color }}
              />
            </motion.button>
          ))}
        </div>
      </div>

      <div className="rounded-3xl p-4" style={glassStyle}>
        <p className="text-gray-800 mb-3 text-[13px] font-bold">Visão Rápida</p>
        <div className="flex flex-col gap-2">
          {stats.map((s) => (
            <div
              key={s.label}
              className="flex items-center gap-3 p-2.5 rounded-2xl"
              style={{
                background: "rgba(255,255,255,0.55)",
                border: "1px solid rgba(255,255,255,0.7)",
              }}
            >
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                style={{
                  background: "rgba(29,95,175,0.09)",
                  border: "1px solid rgba(29,95,175,0.16)",
                }}
              >
                <span className="text-[14px] font-extrabold text-[#1D5FAF]">{s.value}</span>
              </div>
              <div>
                <p className="text-gray-500 text-[10px]">{s.label}</p>
                <p className="text-gray-700 text-[11px] font-semibold">{s.sub}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
