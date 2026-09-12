import { motion } from "motion/react";
import { ChevronRight, Circle, Clock } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { glassStyle, iniciais } from "../../lib/theme";

export type JobItem = {
  id: string;
  title: string;
  client: string;
  detail: string;
  status: "andamento" | "concluido" | "iniciado";
};

const statusConfig = {
  andamento: {
    label: "Em Andamento",
    color: "#A07020",
    bg: "rgba(160,112,32,0.12)",
    border: "rgba(160,112,32,0.22)",
  },
  concluido: {
    label: "Concluído",
    color: "#1E7A4A",
    bg: "rgba(30,122,74,0.12)",
    border: "rgba(30,122,74,0.22)",
  },
  iniciado: {
    label: "Iniciado",
    color: "#1D5FAF",
    bg: "rgba(29,95,175,0.12)",
    border: "rgba(29,95,175,0.22)",
  },
};

export function JobHistory({ jobs }: { jobs: JobItem[] }) {
  const navigate = useNavigate();

  return (
    <div className="rounded-3xl p-4 sm:p-5" style={glassStyle}>
      <div className="flex items-center justify-between mb-4 gap-2">
        <div className="flex items-center gap-2">
          <Clock size={15} className="text-gray-500" />
          <h3 className="text-gray-800 text-[14px] font-bold">Histórico Recente</h3>
        </div>
        <button
          type="button"
          onClick={() => navigate("/app/projetos")}
          className="flex items-center gap-1 px-3 py-1.5 rounded-xl hover:bg-white/50 text-[12px] font-semibold text-[#1D5FAF]"
        >
          Ver todos <ChevronRight size={13} />
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {jobs.length === 0 ? (
          <p className="text-gray-500 text-[13px] p-3">Nenhum projeto ainda.</p>
        ) : null}
        {jobs.map((job, i) => {
          const st = statusConfig[job.status];
          return (
            <motion.button
              key={job.id}
              type="button"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              whileHover={{ scale: 1.005, x: 3 }}
              onClick={() => navigate(`/app/projetos/${job.id}`)}
              className="flex items-center gap-3 p-3 rounded-2xl text-left group w-full"
              style={{
                background: "rgba(255,255,255,0.55)",
                border: "1px solid rgba(255,255,255,0.65)",
              }}
            >
              <div
                className="w-10 h-10 rounded-2xl flex items-center justify-center shrink-0"
                style={{ background: st.bg, border: `1px solid ${st.border}` }}
              >
                <span className="text-[11px] font-bold" style={{ color: st.color }}>
                  {iniciais(job.title)}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-gray-800 truncate text-[13px] font-semibold">{job.title}</p>
                <p className="text-gray-500 truncate text-[11px]">
                  {job.client} · {job.detail}
                </p>
              </div>
              <div
                className="hidden sm:flex items-center gap-1 px-2 py-1 rounded-xl shrink-0"
                style={{ background: st.bg, border: `1px solid ${st.border}` }}
              >
                <Circle size={5} style={{ fill: st.color, color: st.color }} />
                <span className="text-[10px] font-semibold" style={{ color: st.color }}>
                  {st.label}
                </span>
              </div>
              <ChevronRight
                size={14}
                className="text-gray-300 opacity-0 group-hover:opacity-100 shrink-0"
              />
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
