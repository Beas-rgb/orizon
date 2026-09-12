import { motion } from "motion/react";
import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { glassStyle } from "../../lib/theme";

type Counts = { iniciados: number; andamento: number; concluidos: number };

const metrics = [
  {
    key: "iniciados" as const,
    label: "Iniciados",
    color: "#1D5FAF",
    bg: "rgba(29,95,175,0.10)",
    border: "rgba(29,95,175,0.20)",
    tag: "INI",
  },
  {
    key: "andamento" as const,
    label: "Em Andamento",
    color: "#A07020",
    bg: "rgba(160,112,32,0.10)",
    border: "rgba(160,112,32,0.20)",
    tag: "AND",
  },
  {
    key: "concluidos" as const,
    label: "Concluídos",
    color: "#1E7A4A",
    bg: "rgba(30,122,74,0.10)",
    border: "rgba(30,122,74,0.20)",
    tag: "CON",
  },
];

export function MetricsPanel({ counts }: { counts: Counts }) {
  return (
    <div className="rounded-3xl p-4 sm:p-5 flex flex-col gap-5" style={glassStyle}>
      <div>
        <h2 className="text-gray-800 text-[15px] font-bold">Métricas de Trabalhos</h2>
        <p className="text-gray-500 text-[12px]">Resumo dos projetos no seu escopo</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {metrics.map((m, i) => {
          const val = counts[m.key];
          return (
            <motion.div
              key={m.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07, duration: 0.35 }}
              className="rounded-2xl p-4"
              style={{ background: m.bg, border: `1px solid ${m.border}` }}
            >
              <div className="flex items-center justify-between mb-3">
                <div
                  className="px-2 py-0.5 rounded-lg"
                  style={{ background: `${m.color}20`, border: `1px solid ${m.color}30` }}
                >
                  <span
                    className="text-[9px] font-bold tracking-wider"
                    style={{ color: m.color }}
                  >
                    {m.tag}
                  </span>
                </div>
                <div
                  className="flex items-center gap-1 px-1.5 py-0.5 rounded-lg text-[10px] font-bold text-gray-500"
                  style={{ background: "rgba(0,0,0,0.06)" }}
                >
                  <Minus size={10} />0
                </div>
              </div>
              <p className="mb-0.5 text-[30px] font-extrabold leading-none" style={{ color: m.color }}>
                {val}
              </p>
              <p className="text-gray-600 text-[11px] font-medium">{m.label}</p>
            </motion.div>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-4 text-[10px] text-gray-500">
        <span className="inline-flex items-center gap-1.5">
          <TrendingUp size={12} className="text-emerald-700" /> ABERTO → iniciados
        </span>
        <span className="inline-flex items-center gap-1.5">
          <TrendingDown size={12} className="text-amber-700" /> EM_ANDAMENTO
        </span>
        <span>ENCERRADO / ARQUIVADO → concluídos</span>
      </div>
    </div>
  );
}
