/**
 * Tela mínima (Fase 4) — prova endpoints reais sem design.
 * Rota: /consultora/pesquisas-teste
 */
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { api } from "../lib/api";

type PesquisaItem = {
  id: string;
  projeto_id: string;
  titulo: string;
  tipo: string;
  status: string;
  organizacao_nome?: string | null;
};

type Projeto = { id: string; razao_social?: string | null; nome_fantasia?: string | null };

export function ConsultoraPesquisasTestePage() {
  const [itens, setItens] = useState<PesquisaItem[]>([]);
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [erro, setErro] = useState("");
  const [msg, setMsg] = useState("");
  const [projetoId, setProjetoId] = useState("");
  const [titulo, setTitulo] = useState("Pesquisa teste");
  const [tipo, setTipo] = useState("CLIMA");

  async function carregar() {
    setErro("");
    try {
      const [lista, projs] = await Promise.all([
        api<PesquisaItem[]>("/consultora/pesquisas"),
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
  }, []);

  async function criar(ev: FormEvent) {
    ev.preventDefault();
    setMsg("");
    setErro("");
    try {
      await api(`/projetos/${projetoId}/pesquisas`, {
        method: "POST",
        json: { titulo, tipo },
      });
      setMsg("Pesquisa criada.");
      await carregar();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro ao criar");
    }
  }

  return (
    <AppShell active="pesquisas">
      <h1 className="text-lg font-bold mb-2">Teste — pesquisas (API)</h1>
      <p className="text-xs text-gray-500 mb-4">
        Tela de prova. UI definitiva em{" "}
        <Link className="underline text-[#1D5FAF]" to="/consultora/pesquisas">
          /consultora/pesquisas
        </Link>
        .
      </p>
      {erro ? <p className="text-red-700 text-sm mb-2">{erro}</p> : null}
      {msg ? <p className="text-green-700 text-sm mb-2">{msg}</p> : null}

      <form onSubmit={(e) => void criar(e)} className="mb-6 flex flex-col gap-2 max-w-md">
        <label className="text-xs">
          Projeto
          <select
            className="block w-full border p-2 mt-1"
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
        <label className="text-xs">
          Título
          <input
            className="block w-full border p-2 mt-1"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
          />
        </label>
        <label className="text-xs">
          Tipo
          <select
            className="block w-full border p-2 mt-1"
            value={tipo}
            onChange={(e) => setTipo(e.target.value)}
          >
            <option value="CLIMA">CLIMA</option>
            <option value="DESEMPENHO">DESEMPENHO</option>
            <option value="DIAGNOSTICO_ORGANIZACIONAL">DIAGNOSTICO_ORGANIZACIONAL</option>
          </select>
        </label>
        <button type="submit" className="bg-[#1D5FAF] text-white px-3 py-2 text-sm font-bold">
          Criar pesquisa
        </button>
      </form>

      <pre className="text-[11px] bg-white/70 p-3 overflow-auto rounded border">
        {JSON.stringify(itens, null, 2)}
      </pre>
      <ul className="mt-4 text-sm">
        {itens.map((item) => (
          <li key={item.id} className="mb-1">
            <Link
              className="text-[#1D5FAF] underline"
              to={`/projetos/${item.projeto_id}/pesquisas/${item.id}`}
            >
              {item.titulo}
            </Link>{" "}
            — {item.organizacao_nome || "?"} · {item.tipo} · {item.status}
          </li>
        ))}
      </ul>
    </AppShell>
  );
}
