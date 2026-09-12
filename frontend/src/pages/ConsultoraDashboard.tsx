import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { JobHistory, type JobItem } from "../components/dashboard/JobHistory";
import { MetricsPanel } from "../components/dashboard/MetricsPanel";
import { QuickAccess } from "../components/dashboard/QuickAccess";
import { SmartBriefing } from "../components/dashboard/SmartBriefing";
import { AppShell } from "../components/layout/AppShell";
import { api } from "../lib/api";

type Projeto = {
  id: string;
  estado: string;
  rotulo: string;
  vinculo_titulo?: string | null;
  nome_fantasia?: string | null;
  razao_social?: string | null;
};

const ENCERRADOS = new Set(["ENCERRADO", "ARQUIVADO"]);

function nomeCliente(p: Projeto) {
  return p.nome_fantasia || p.razao_social || "Cliente";
}

function statusDe(estado: string): JobItem["status"] {
  if (ENCERRADOS.has(estado)) return "concluido";
  if (estado === "EM_ANDAMENTO") return "andamento";
  return "iniciado";
}

export function ConsultoraDashboard() {
  const { usuario } = useAuth();
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Projeto[]>("/projetos")
      .then(setProjetos)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  const counts = useMemo(() => {
    const iniciados = projetos.filter((p) => p.estado === "ABERTO").length;
    const andamento = projetos.filter((p) => p.estado === "EM_ANDAMENTO").length;
    const concluidos = projetos.filter((p) => ENCERRADOS.has(p.estado)).length;
    return { iniciados, andamento, concluidos };
  }, [projetos]);

  const jobs: JobItem[] = projetos.slice(0, 6).map((p) => ({
    id: p.id,
    title: p.vinculo_titulo || nomeCliente(p),
    client: nomeCliente(p),
    detail: `${p.rotulo} · ${p.estado}`,
    status: statusDe(p.estado),
  }));

  const hints = projetos.slice(0, 5).map((p) => ({
    type: "Trabalho",
    label: p.vinculo_titulo || nomeCliente(p),
    icon: "💼",
  }));

  return (
    <AppShell active="dashboard" searchHints={hints}>
      {erro ? <p className="mb-4 text-[13px] text-[#A02828]">{erro}</p> : null}
      <div className="flex flex-col lg:flex-row gap-5 items-start">
        <QuickAccess
          stats={[
            { label: "Abertos", value: String(counts.iniciados), sub: "projetos" },
            { label: "Andamento", value: String(counts.andamento), sub: "projetos" },
            { label: "Total", value: String(projetos.length), sub: "trabalhos" },
          ]}
        />
        <div className="flex-1 flex flex-col gap-5 min-w-0 w-full">
          <MetricsPanel counts={counts} />
          <JobHistory jobs={jobs} />
          <SmartBriefing
            nome={usuario?.nome || "Consultora"}
            priority={jobs.slice(0, 3).map((j) => ({
              id: j.id,
              task: j.title,
              deadline: j.detail,
              tone: j.status === "andamento" ? "warn" : j.status === "iniciado" ? "danger" : "ok",
            }))}
            indicators={[
              { label: "Trabalhos no painel", value: String(projetos.length), unit: "total" },
              { label: "Em andamento", value: String(counts.andamento), unit: "agora" },
              { label: "Concluídos", value: String(counts.concluidos), unit: "encerrados" },
            ]}
          />
        </div>
      </div>
    </AppShell>
  );
}
