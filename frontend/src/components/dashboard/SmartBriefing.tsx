import { motion } from "motion/react";
import {
  AlertTriangle,
  BarChart2,
  Calendar,
  ChevronRight,
  ClipboardList,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ACCENT, glassStyle } from "../../lib/theme";

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

function getFormattedDate() {
  return new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

type Props = {
  nome: string;
  priority: { id: string; task: string; deadline: string; tone: "danger" | "warn" | "ok" }[];
  indicators: { label: string; value: string; unit: string }[];
};

const toneMap = {
  danger: { color: "var(--hz-danger)", bg: "var(--hz-danger-09)", border: "var(--hz-danger-20)" },
  warn: { color: "var(--hz-warn)", bg: "var(--hz-warn-09)", border: "var(--hz-warn-20)" },
  ok: { color: "var(--hz-ok)", bg: "var(--hz-ok-09)", border: "var(--hz-ok-20)" },
};

export function SmartBriefing({ nome, priority, indicators }: Props) {
  const [time, setTime] = useState(new Date());
  const [checked, setChecked] = useState<string[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const timeStr = time.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="rounded-3xl p-4 sm:p-5" style={glassStyle}>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        <div
          className="rounded-2xl p-4 flex flex-col justify-between"
          style={{ background: "var(--hz-accent-08)", border: "1px solid var(--hz-accent-18)" }}
        >
          <div>
            <div className="flex items-center gap-2 mb-3">
              <ClipboardList size={14} style={{ color: ACCENT }} />
              <span className="text-[11px] font-semibold" style={{ color: ACCENT }}>
                Resumo do Dia
              </span>
            </div>
            <p className="text-gray-500 mb-1 text-[11px]">
              {getGreeting()}, {nome.split(" ")[0]}
            </p>
            <p className="text-gray-800 text-[26px] font-extrabold leading-tight">{timeStr}</p>
            <p className="text-gray-400 mt-1 capitalize text-[10px]">{getFormattedDate()}</p>
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={13} style={{ color: "var(--hz-danger)" }} />
            <p className="text-gray-800 text-[13px] font-bold">Prioridades</p>
          </div>
          <div className="flex flex-col gap-2">
            {priority.length === 0 ? (
              <p className="text-gray-500 text-[12px]">Nada urgente no momento.</p>
            ) : null}
            {priority.map((task) => {
              const tone = toneMap[task.tone];
              const done = checked.includes(task.id);
              return (
                <motion.button
                  key={task.id}
                  type="button"
                  whileHover={{ scale: 1.015 }}
                  className="flex items-start gap-2.5 p-3 rounded-2xl text-left"
                  style={{
                    background: done ? "var(--hz-ok-08)" : tone.bg,
                    border: `1px solid ${done ? "var(--hz-ok-20)" : tone.border}`,
                    opacity: done ? 0.55 : 1,
                  }}
                  onClick={() =>
                    setChecked((prev) =>
                      prev.includes(task.id)
                        ? prev.filter((t) => t !== task.id)
                        : [...prev, task.id],
                    )
                  }
                >
                  <div
                    className="w-5 h-5 rounded-lg flex items-center justify-center shrink-0 mt-0.5 text-white text-[10px]"
                    style={{
                      background: done ? "var(--hz-ok)" : "var(--hz-white-75)",
                      border: `1px solid ${done ? "var(--hz-ok)" : "var(--hz-black-12)"}`,
                    }}
                  >
                    {done ? "✓" : ""}
                  </div>
                  <div className="min-w-0">
                    <p
                      className="text-gray-700 text-[11px] font-medium leading-tight"
                      style={{ textDecoration: done ? "line-through" : "none" }}
                    >
                      {task.task}
                    </p>
                    <div className="flex items-center gap-1 mt-1">
                      <Calendar size={9} style={{ color: tone.color }} />
                      <span className="text-[10px] font-bold" style={{ color: tone.color }}>
                        {task.deadline}
                      </span>
                    </div>
                  </div>
                </motion.button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 size={13} style={{ color: ACCENT }} />
            <p className="text-gray-800 text-[13px] font-bold">Indicadores</p>
          </div>
          <div className="flex flex-col gap-2">
            {indicators.map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between p-3 rounded-2xl gap-2"
                style={{
                  background: "var(--hz-white-55)",
                  border: "1px solid var(--hz-white-70)",
                }}
              >
                <p className="text-gray-600 text-[11px]">{item.label}</p>
                <div className="text-right shrink-0">
                  <span className="text-gray-800 text-[15px] font-extrabold">{item.value}</span>
                  <span className="text-gray-400 ml-1 text-[10px]">{item.unit}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-3">
            <Zap size={13} style={{ color: "var(--hz-warn)" }} />
            <p className="text-gray-800 text-[13px] font-bold">Ações Rápidas</p>
          </div>
          <div className="flex flex-col gap-2">
            {[
              { label: "Criar novo projeto", to: "/projetos/novo", color: ACCENT },
              { label: "Ver trabalhos", to: "/projetos", color: "var(--hz-ok)" },
            ].map((a) => (
              <motion.button
                key={a.label}
                type="button"
                whileHover={{ x: 3, scale: 1.01 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate(a.to)}
                className="flex items-center gap-2.5 p-2.5 rounded-xl group text-left"
                style={{
                  background: "var(--hz-white-55)",
                  border: "1px solid var(--hz-white-70)",
                }}
              >
                <div className="w-2 h-2 rounded-full shrink-0" style={{ background: a.color }} />
                <span className="flex-1 text-gray-700 text-[11px] font-medium">{a.label}</span>
                <ChevronRight
                  size={12}
                  className="opacity-0 group-hover:opacity-70"
                  style={{ color: a.color }}
                />
              </motion.button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
