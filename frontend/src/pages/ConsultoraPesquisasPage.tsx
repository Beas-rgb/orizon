/**
 * Painel definitivo — Pesquisas e Avaliações da consultora.
 * Rota: /consultora/pesquisas (basename /app).
 */
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { api } from "../lib/api";
import { ACCENT, glassStyle } from "../lib/theme";

type Aba = "visao" | "pesquisas" | "modelos" | "organizacao";

type PesquisaItem = {
  id: string;
  projeto_id: string;
  titulo: string;
  tipo: string;
  status: string;
  organizacao_id?: string | null;
  organizacao_nome?: string | null;
  criado_em?: string | null;
};

type Projeto = {
  id: string;
  organizacao_id?: string;
  razao_social?: string | null;
  nome_fantasia?: string | null;
};

type Modelo = { id: string; nome: string; tipo: string; categoria: string };

const TIPOS_UI = [
  { value: "CLIMA", label: "Clima organizacional" },
  { value: "DESEMPENHO", label: "Desempenho" },
  { value: "DIAGNOSTICO_ORGANIZACIONAL", label: "Diagnóstico organizacional" },
];

function rotuloStatus(status: string) {
  if (status === "PUBLICADA") return "Em andamento";
  if (status === "ENCERRADA") return "Encerrada";
  if (status === "RASCUNHO") return "Rascunho";
  if (status === "AGENDADA") return "Agendada";
  return status;
}

export function ConsultoraPesquisasPage() {
  const navigate = useNavigate();
  const [aba, setAba] = useState<Aba>("pesquisas");
  const [itens, setItens] = useState<PesquisaItem[]>([]);
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [erro, setErro] = useState("");
  const [msg, setMsg] = useState("");
  const [filtroOrg, setFiltroOrg] = useState("");
  const [filtroTipo, setFiltroTipo] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [filtroAno, setFiltroAno] = useState("");
  const [mostrarNova, setMostrarNova] = useState(false);
  const [projetoId, setProjetoId] = useState("");
  const [titulo, setTitulo] = useState("");
  const [tipo, setTipo] = useState("CLIMA");

  async function carregar() {
    setErro("");
    const params = new URLSearchParams();
    if (filtroOrg) params.set("organizacao_id", filtroOrg);
    if (filtroTipo) params.set("tipo", filtroTipo);
    if (filtroStatus) params.set("status", filtroStatus);
    if (filtroAno) params.set("ano", filtroAno);
    const qs = params.toString() ? `?${params}` : "";
    try {
      const [lista, projs] = await Promise.all([
        api<PesquisaItem[]>(`/consultora/pesquisas${qs}`),
        api<Projeto[]>("/projetos"),
      ]);
      setItens(lista);
      setProjetos(projs);
      if (!projetoId && projs[0]) setProjetoId(projs[0].id);
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  useEffect(() => {
    void carregar();
  }, [filtroOrg, filtroTipo, filtroStatus, filtroAno]);

  useEffect(() => {
    if (aba !== "modelos") return;
    api<Modelo[]>("/modelos")
      .then(setModelos)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, [aba]);

  const orgs = useMemo(() => {
    const mapa = new Map<string, string>();
    for (const p of projetos) {
      if (p.organizacao_id) {
        mapa.set(
          p.organizacao_id,
          p.nome_fantasia || p.razao_social || p.organizacao_id,
        );
      }
    }
    for (const item of itens) {
      if (item.organizacao_id && item.organizacao_nome) {
        mapa.set(item.organizacao_id, item.organizacao_nome);
      }
    }
    return [...mapa.entries()];
  }, [projetos, itens]);

  const resumo = useMemo(() => {
    const publicadas = itens.filter((i) => i.status === "PUBLICADA").length;
    const rascunhos = itens.filter((i) => i.status === "RASCUNHO").length;
    const encerradas = itens.filter((i) => i.status === "ENCERRADA").length;
    return { publicadas, rascunhos, encerradas, total: itens.length };
  }, [itens]);

  async function criar(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    setErro("");
    try {
      const criada = await api<PesquisaItem>(`/projetos/${projetoId}/pesquisas`, {
        method: "POST",
        json: { titulo: titulo.trim(), tipo },
      });
      setMsg("Pesquisa criada.");
      setMostrarNova(false);
      setTitulo("");
      await carregar();
      navigate(`/projetos/${criada.projeto_id}/pesquisas/${criada.id}`);
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro ao criar");
    }
  }

  const abas: { id: Aba; label: string }[] = [
    { id: "visao", label: "Visão geral" },
    { id: "pesquisas", label: "Pesquisas" },
    { id: "modelos", label: "Modelos" },
    { id: "organizacao", label: "Organização" },
  ];

  return (
    <AppShell active="pesquisas">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h1 className="text-[18px] font-bold text-gray-800 mb-1">
            Pesquisas e Avaliações
          </h1>
          <p className="text-[12px] text-gray-500">
            Todas as pesquisas dos seus trabalhos. Regras de acesso ficam na API.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setMostrarNova(true)}
          className="rounded-xl px-4 py-2 text-white text-[13px] font-bold"
          style={{ background: ACCENT }}
        >
          + Nova pesquisa
        </button>
      </div>

      <nav className="flex flex-wrap gap-2 mb-5">
        {abas.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setAba(item.id)}
            className="rounded-full px-3 py-1.5 text-[12px] font-semibold"
            style={{
              background:
                aba === item.id ? "rgba(29,95,175,0.15)" : "rgba(255,255,255,0.55)",
              border:
                aba === item.id
                  ? "1px solid rgba(29,95,175,0.3)"
                  : "1px solid transparent",
              color: aba === item.id ? "#1D5FAF" : "#4b5563",
            }}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}
      {msg ? <p className="text-[#1E7A4A] text-[13px] mb-3">{msg}</p> : null}

      {mostrarNova ? (
        <form
          onSubmit={(e) => void criar(e)}
          className="rounded-3xl p-5 mb-5 max-w-lg"
          style={glassStyle}
        >
          <h2 className="text-[14px] font-bold mb-3">Nova pesquisa</h2>
          <label className="block text-[12px] text-gray-600 mb-2">
            Organização / projeto
            <select
              required
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-[13px]"
              value={projetoId}
              onChange={(e) => setProjetoId(e.target.value)}
            >
              {projetos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome_fantasia || p.razao_social || p.id}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-[12px] text-gray-600 mb-2">
            Tipo
            <select
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-[13px]"
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
            >
              {TIPOS_UI.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-[12px] text-gray-600 mb-3">
            Nome
            <input
              required
              minLength={2}
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-[13px]"
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Ex.: Avaliação de Desempenho 2026"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              className="rounded-xl px-4 py-2 text-white text-[13px] font-bold"
              style={{ background: ACCENT }}
            >
              Criar
            </button>
            <button
              type="button"
              className="rounded-xl px-4 py-2 text-[13px] text-gray-600"
              onClick={() => setMostrarNova(false)}
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}

      {aba === "visao" ? (
        <div className="grid sm:grid-cols-4 gap-3 mb-5">
          {[
            ["Total", resumo.total],
            ["Em andamento", resumo.publicadas],
            ["Rascunhos", resumo.rascunhos],
            ["Encerradas", resumo.encerradas],
          ].map(([k, v]) => (
            <div key={k as string} className="rounded-3xl p-4" style={glassStyle}>
              <p className="text-[11px] text-gray-500">{k}</p>
              <p className="text-[20px] font-bold text-gray-800 mt-1">{v}</p>
            </div>
          ))}
        </div>
      ) : null}

      {aba === "pesquisas" || aba === "visao" ? (
        <>
          <div className="flex flex-wrap gap-2 mb-4">
            <select
              className="rounded-xl border border-gray-200 px-3 py-2 text-[12px]"
              value={filtroOrg}
              onChange={(e) => setFiltroOrg(e.target.value)}
            >
              <option value="">Organização</option>
              {orgs.map(([id, nome]) => (
                <option key={id} value={id}>
                  {nome}
                </option>
              ))}
            </select>
            <select
              className="rounded-xl border border-gray-200 px-3 py-2 text-[12px]"
              value={filtroTipo}
              onChange={(e) => setFiltroTipo(e.target.value)}
            >
              <option value="">Tipo</option>
              {TIPOS_UI.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <select
              className="rounded-xl border border-gray-200 px-3 py-2 text-[12px]"
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
            >
              <option value="">Status</option>
              <option value="RASCUNHO">Rascunho</option>
              <option value="PUBLICADA">Em andamento</option>
              <option value="ENCERRADA">Encerrada</option>
            </select>
            <input
              type="number"
              placeholder="Ano"
              className="rounded-xl border border-gray-200 px-3 py-2 text-[12px] w-24"
              value={filtroAno}
              onChange={(e) => setFiltroAno(e.target.value)}
            />
          </div>
          <ul className="flex flex-col gap-2">
            {itens.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/projetos/${item.projeto_id}/pesquisas/${item.id}`}
                  className="block rounded-3xl p-4 hover:bg-white/70 transition-colors"
                  style={glassStyle}
                >
                  <p className="text-[14px] font-bold text-gray-800">{item.titulo}</p>
                  <p className="text-[12px] text-gray-500 mt-0.5">
                    {item.organizacao_nome || "Organização"} · {item.tipo} ·{" "}
                    {rotuloStatus(item.status)}
                  </p>
                </Link>
              </li>
            ))}
            {itens.length === 0 ? (
              <p className="text-gray-500 text-[13px]">Nenhuma pesquisa encontrada.</p>
            ) : null}
          </ul>
        </>
      ) : null}

      {aba === "modelos" ? (
        <ul className="flex flex-col gap-2">
          {modelos.map((m) => (
            <li key={m.id} className="rounded-3xl p-4" style={glassStyle}>
              <p className="text-[14px] font-bold">{m.nome}</p>
              <p className="text-[12px] text-gray-500">
                {m.tipo} · {m.categoria}
              </p>
            </li>
          ))}
          {modelos.length === 0 ? (
            <p className="text-gray-500 text-[13px]">
              Nenhum modelo ainda. Salve um a partir de uma pesquisa.
            </p>
          ) : null}
        </ul>
      ) : null}

      {aba === "organizacao" ? (
        <div className="rounded-3xl p-5" style={glassStyle}>
          <p className="text-[13px] text-gray-600">
            Use <Link className="text-[#1D5FAF] font-semibold underline" to="/projetos">
              Trabalhos
            </Link>{" "}
            para abrir cada projeto, equipe e configuração. A listagem de pesquisas
            acima já agrega todas as organizações no seu escopo.
          </p>
        </div>
      ) : null}
    </AppShell>
  );
}
