import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { api } from "../lib/api";
import { ACCENT, glassStyle } from "../lib/theme";

type Projeto = {
  id: string;
  estado: string;
  rotulo: string;
  vinculo_titulo?: string | null;
  nome_fantasia?: string | null;
  razao_social?: string | null;
};

type Rotulo = { id: string; nome: string };

function nomeCliente(p: Projeto) {
  return p.nome_fantasia || p.razao_social || "Cliente";
}

export function ProjetosListaPage() {
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Projeto[]>("/projetos")
      .then(setProjetos)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  return (
    <AppShell active="projetos">
      <div className="flex items-center justify-between mb-5 gap-3 flex-wrap">
        <div>
          <h1 className="text-[18px] font-bold text-gray-800">Trabalhos</h1>
          <p className="text-[12px] text-gray-500">Lista de projetos da consultora</p>
        </div>
        <Link
          to="/app/projetos/novo"
          className="px-4 py-2.5 rounded-2xl text-white text-[13px] font-bold"
          style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
        >
          Novo projeto
        </Link>
      </div>
      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}
      <div className="rounded-3xl p-4 sm:p-5" style={glassStyle}>
        <ul className="flex flex-col gap-2">
          {projetos.map((p) => (
            <li key={p.id}>
              <Link
                to={`/app/projetos/${p.id}`}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 p-3 rounded-2xl hover:bg-white/60"
                style={{
                  background: "rgba(255,255,255,0.55)",
                  border: "1px solid rgba(255,255,255,0.65)",
                }}
              >
                <div>
                  <p className="text-[13px] font-semibold text-gray-800">
                    {p.vinculo_titulo || nomeCliente(p)}
                  </p>
                  <p className="text-[11px] text-gray-500">
                    {nomeCliente(p)} · {p.rotulo}
                  </p>
                </div>
                <span className="text-[11px] font-bold text-[#1D5FAF]">{p.estado}</span>
              </Link>
            </li>
          ))}
          {projetos.length === 0 && !erro ? (
            <p className="text-gray-500 text-[13px] p-2">Nenhum projeto. Crie o primeiro.</p>
          ) : null}
        </ul>
      </div>
    </AppShell>
  );
}

export function NovoProjetoPage() {
  const [rotulos, setRotulos] = useState<Rotulo[]>([]);
  const [erro, setErro] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api<Rotulo[]>("/projetos/rotulos")
      .then(setRotulos)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  async function criar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    const form = evento.currentTarget;
    try {
      const cnpjBruto = (form.elements.namedItem("cnpj") as HTMLInputElement).value;
      const cnpj = cnpjBruto.replace(/[^0-9A-Za-z]/g, "").toUpperCase();
      if (cnpj.length !== 14) {
        setErro("CNPJ deve ter 14 caracteres (pode colar com pontuação).");
        return;
      }
      const criado = await api<Projeto>("/projetos", {
        method: "POST",
        json: {
          rotulo_id: (form.elements.namedItem("rotulo_id") as HTMLSelectElement).value,
          cnpj,
          email_orgao: (form.elements.namedItem("email_orgao") as HTMLInputElement).value.trim(),
          vinculo_tipo: (form.elements.namedItem("vinculo_tipo") as HTMLSelectElement).value,
          vinculo_titulo: (form.elements.namedItem("vinculo_titulo") as HTMLInputElement).value.trim(),
        },
      });
      navigate(`/app/projetos/${criado.id}`);
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro ao criar");
    }
  }

  const field =
    "mt-1 w-full rounded-xl px-3 py-2.5 outline-none bg-white/70 border border-white/80 text-[13px]";

  return (
    <AppShell active="novo">
      <h1 className="text-[18px] font-bold text-gray-800 mb-1">Novo projeto</h1>
      <p className="text-[12px] text-gray-500 mb-5">
        CNPJ cria/atualiza a organização; o e-mail recebe o convite do órgão.
      </p>
      <form
        onSubmit={criar}
        className="rounded-3xl p-5 max-w-xl flex flex-col gap-3"
        style={glassStyle}
      >
        <label className="text-[12px] font-semibold text-gray-600">
          Rótulo
          <select name="rotulo_id" required className={field}>
            <option value="">Selecione</option>
            {rotulos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.nome}
              </option>
            ))}
          </select>
        </label>
        <label className="text-[12px] font-semibold text-gray-600">
          CNPJ
          <input
            name="cnpj"
            required
            placeholder="00.000.000/0001-00"
            className={field}
          />
        </label>
        <p className="text-[11px] text-gray-400 -mt-2">
          Use um CNPJ real (BrasilAPI). Ex.: 33000167000101
        </p>
        <label className="text-[12px] font-semibold text-gray-600">
          E-mail do órgão
          <input name="email_orgao" type="email" required className={field} />
        </label>
        <label className="text-[12px] font-semibold text-gray-600">
          Tipo de vínculo
          <select name="vinculo_tipo" required className={field}>
            <option value="EDITAL">Edital</option>
            <option value="DOCUMENTO">Documento</option>
          </select>
        </label>
        <label className="text-[12px] font-semibold text-gray-600">
          Título do vínculo
          <input name="vinculo_titulo" required className={field} />
        </label>
        {erro ? <p className="text-[13px] text-[#A02828]">{erro}</p> : null}
        <button
          type="submit"
          className="rounded-2xl py-3 text-white text-[14px] font-bold mt-2"
          style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
        >
          Criar projeto
        </button>
      </form>
    </AppShell>
  );
}

type Pesquisa = { id: string; titulo: string; tipo: string; status: string };
type Membro = { nome: string; email: string; papel: string; situacao: string };
type Setor = { id: string; nome: string };
type Doc = { id: string; nome: string; visibilidade?: string };

export function ProjetoDetalhePage() {
  const { id } = useParams();
  const [aba, setAba] = useState<"resumo" | "equipe" | "pesquisas" | "docs" | "config">(
    "resumo",
  );
  const [projeto, setProjeto] = useState<Projeto | null>(null);
  const [pesquisas, setPesquisas] = useState<Pesquisa[]>([]);
  const [equipe, setEquipe] = useState<Membro[]>([]);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [aviso, setAviso] = useState("");
  const [conviteMsg, setConviteMsg] = useState("");

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api<Projeto>(`/projetos/${id}`),
      api<Pesquisa[]>(`/projetos/${id}/pesquisas`),
      api<Membro[]>(`/projetos/${id}/equipe`).catch(() => []),
      api<Setor[]>(`/projetos/${id}/setores`).catch(() => []),
      api<Doc[]>(`/biblioteca?projeto_id=${id}`).catch(() => []),
    ])
      .then(([p, pe, eq, se, d]) => {
        setProjeto(p);
        setPesquisas(pe);
        setEquipe(eq);
        setSetores(se);
        setDocs(d);
      })
      .catch((exc) => setAviso(exc instanceof Error ? exc.message : "Erro"));
  }, [id]);

  async function convidarFuncionario(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!id) return;
    setConviteMsg("");
    const form = evento.currentTarget;
    try {
      const resp = await api<{ mensagem: string }>("/auth/convites", {
        method: "POST",
        json: {
          nome: (form.elements.namedItem("nome") as HTMLInputElement).value,
          email: (form.elements.namedItem("email") as HTMLInputElement).value,
          papel: "FUNCIONARIO",
          projeto_id: id,
        },
      });
      setConviteMsg(resp.mensagem || "Convite enviado.");
      form.reset();
      setEquipe(await api<Membro[]>(`/projetos/${id}/equipe`));
    } catch (exc) {
      setConviteMsg(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function criarPesquisa(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!id) return;
    setAviso("");
    const form = evento.currentTarget;
    try {
      await api(`/projetos/${id}/pesquisas`, {
        method: "POST",
        json: {
          titulo: (form.elements.namedItem("titulo") as HTMLInputElement).value,
          tipo: (form.elements.namedItem("tipo") as HTMLSelectElement).value,
        },
      });
      setPesquisas(await api<Pesquisa[]>(`/projetos/${id}/pesquisas`));
      form.reset();
    } catch (exc) {
      setAviso(exc instanceof Error ? exc.message : "Erro");
    }
  }

  const abas = [
    ["resumo", "Resumo"],
    ["equipe", "Equipe"],
    ["pesquisas", "Pesquisas"],
    ["docs", "Biblioteca"],
    ["config", "Config"],
  ] as const;

  const field =
    "mt-1 w-full rounded-xl px-3 py-2.5 outline-none bg-white/70 border border-white/80 text-[13px]";

  return (
    <AppShell active="projetos">
      <Link to="/app/projetos" className="text-[12px] text-[#1D5FAF] font-semibold">
        ← Voltar aos trabalhos
      </Link>
      <h1 className="text-[18px] font-bold text-gray-800 mt-2">
        {projeto ? projeto.vinculo_titulo || nomeCliente(projeto) : "Carregando…"}
      </h1>
      {projeto ? (
        <p className="text-[12px] text-gray-500 mb-4">
          {nomeCliente(projeto)} · {projeto.rotulo} · {projeto.estado}
        </p>
      ) : null}

      <div
        className="flex gap-1 p-1 rounded-2xl mb-4 overflow-x-auto"
        style={{ background: "rgba(0,0,0,0.05)", border: "1px solid rgba(255,255,255,0.55)" }}
      >
        {abas.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setAba(key)}
            className="px-3 py-1.5 rounded-xl text-[12px] whitespace-nowrap"
            style={{
              fontWeight: aba === key ? 700 : 400,
              background: aba === key ? "rgba(255,255,255,0.9)" : "transparent",
              color: aba === key ? ACCENT : "#9ca3af",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {aviso ? <p className="text-[#A02828] text-[13px] mb-3">{aviso}</p> : null}

      <div className="rounded-3xl p-4 sm:p-5" style={glassStyle}>
        {aba === "resumo" && (
          <div className="grid sm:grid-cols-3 gap-3">
            <Stat label="Pesquisas" value={String(pesquisas.length)} />
            <Stat label="Equipe" value={String(equipe.length)} />
            <Stat label="Setores" value={String(setores.length)} />
          </div>
        )}

        {aba === "equipe" && (
          <div className="flex flex-col gap-4">
            <ul className="flex flex-col gap-2">
              {equipe.map((m) => (
                <li
                  key={`${m.email}-${m.papel}`}
                  className="p-3 rounded-2xl text-[13px]"
                  style={{ background: "rgba(255,255,255,0.55)" }}
                >
                  <strong>{m.nome}</strong>
                  <span className="text-gray-500 text-[11px] ml-2">
                    {m.email} · {m.papel} · {m.situacao}
                  </span>
                </li>
              ))}
              {equipe.length === 0 ? (
                <p className="text-gray-500 text-[13px]">Ninguém na equipe ainda.</p>
              ) : null}
            </ul>
            <form onSubmit={convidarFuncionario} className="grid sm:grid-cols-3 gap-2 items-end">
              <label className="text-[12px] font-semibold text-gray-600">
                Nome
                <input name="nome" required className={field} />
              </label>
              <label className="text-[12px] font-semibold text-gray-600">
                E-mail
                <input name="email" type="email" required className={field} />
              </label>
              <button
                type="submit"
                className="rounded-xl py-2.5 text-white text-[13px] font-bold"
                style={{ background: ACCENT }}
              >
                Convidar funcionário
              </button>
            </form>
            {conviteMsg ? <p className="text-[12px] text-gray-600">{conviteMsg}</p> : null}
          </div>
        )}

        {aba === "pesquisas" && (
          <div className="flex flex-col gap-4">
            <ul className="flex flex-col gap-2">
              {pesquisas.map((p) => (
                <li
                  key={p.id}
                  className="p-3 rounded-2xl flex justify-between gap-2"
                  style={{ background: "rgba(255,255,255,0.55)" }}
                >
                  <div>
                    <p className="text-[13px] font-semibold">{p.titulo}</p>
                    <p className="text-[11px] text-gray-500">
                      {p.tipo} · {p.status}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
            <form onSubmit={criarPesquisa} className="grid sm:grid-cols-3 gap-2 items-end">
              <label className="text-[12px] font-semibold text-gray-600 sm:col-span-1">
                Título
                <input name="titulo" required className={field} />
              </label>
              <label className="text-[12px] font-semibold text-gray-600">
                Tipo
                <select name="tipo" className={field} defaultValue="CLIMA">
                  <option value="CLIMA">Clima</option>
                  <option value="DESEMPENHO">Desempenho</option>
                  <option value="CARGOS_SALARIOS">Cargos e salários</option>
                  <option value="PERSONALIZADA">Personalizada</option>
                </select>
              </label>
              <button
                type="submit"
                className="rounded-xl py-2.5 text-white text-[13px] font-bold"
                style={{ background: ACCENT }}
              >
                Criar pesquisa
              </button>
            </form>
          </div>
        )}

        {aba === "docs" && (
          <ul className="flex flex-col gap-2">
            {docs.map((d) => (
              <li
                key={d.id}
                className="p-3 rounded-2xl text-[13px]"
                style={{ background: "rgba(255,255,255,0.55)" }}
              >
                {d.nome}
                {d.visibilidade ? (
                  <span className="text-[11px] text-gray-500 ml-2">{d.visibilidade}</span>
                ) : null}
              </li>
            ))}
            {docs.length === 0 ? (
              <p className="text-gray-500 text-[13px]">Nenhum documento neste projeto.</p>
            ) : null}
          </ul>
        )}

        {aba === "config" && (
          <div>
            <p className="text-[13px] text-gray-600 mb-2">Setores cadastrados</p>
            <ul className="flex flex-wrap gap-2">
              {setores.map((s) => (
                <li
                  key={s.id}
                  className="px-3 py-1.5 rounded-xl text-[12px] font-semibold"
                  style={{ background: "rgba(29,95,175,0.10)", color: ACCENT }}
                >
                  {s.nome}
                </li>
              ))}
              {setores.length === 0 ? (
                <p className="text-gray-500 text-[13px]">Nenhum setor.</p>
              ) : null}
            </ul>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-2xl p-4"
      style={{ background: "rgba(29,95,175,0.08)", border: "1px solid rgba(29,95,175,0.18)" }}
    >
      <p className="text-[11px] text-gray-500">{label}</p>
      <p className="text-[28px] font-extrabold text-[#1D5FAF]">{value}</p>
    </div>
  );
}
