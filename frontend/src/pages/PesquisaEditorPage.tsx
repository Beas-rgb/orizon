import { useCallback, useEffect, useState, type DragEvent, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArvoreOrganizacional } from "../components/estrutura/ArvoreOrganizacional";
import type { NoArvore } from "../components/estrutura/tipos";
import { AppShell } from "../components/layout/AppShell";
import { api, tokenAtual, urlApi } from "../lib/api";
import { ACCENT, glassStyle } from "../lib/theme";

type Ciclo = {
  id: string;
  nome: string;
  escopo: string;
  status: string;
  configuracao?: string | null;
};

type Relacao = {
  id: string;
  avaliador_id: string;
  avaliado_id: string;
  avaliador_nome?: string;
  avaliado_nome?: string;
  tipo_relacao: string;
  peso: number;
  status: string;
};

const PESOS_PADRAO = { AUTO: 1, SUPERIOR: 2, SUBORDINADO: 1 };

type Pesquisa = {
  id: string;
  titulo: string;
  tipo: string;
  status: string;
  descricao?: string | null;
};

type Opcao = { id: string; texto: string; ordem?: number };
type Pergunta = {
  id: string;
  pesquisa_id?: string | null;
  texto: string;
  tipo: string;
  obrigatoria: boolean;
  ordem: number;
  opcoes: Opcao[];
  midia_tipo?: string | null;
  tem_midia?: boolean;
};

type Participante = {
  usuario_id: string;
  nome: string;
  email: string;
  status: string;
};

type ParticipantesResp = {
  agregado: boolean;
  total?: number | null;
  respondidas?: number | null;
  itens?: Participante[] | null;
};

const field =
  "mt-1 w-full rounded-xl px-3 py-2.5 text-[13px] outline-none bg-white/70 border border-white/80";

/**
 * Editor de rascunho: editar/reordenar/mídia, participantes e preview.
 */
export function PesquisaEditorPage() {
  const { projetoId = "", pesquisaId = "" } = useParams();
  const navigate = useNavigate();
  const [pesquisa, setPesquisa] = useState<Pesquisa | null>(null);
  const [perguntas, setPerguntas] = useState<Pergunta[]>([]);
  const [participantes, setParticipantes] = useState<Participante[]>([]);
  const [totalNominal, setTotalNominal] = useState(0);
  const [resumoParticipantes, setResumoParticipantes] = useState<{
    total: number;
    respondidas: number;
  } | null>(null);
  const [aba, setAba] = useState<
    | "geral"
    | "estrutura"
    | "perguntas"
    | "participantes"
    | "perspectivas"
    | "pesos"
    | "regras"
    | "preview"
    | "aplicacao"
    | "resultados"
    | "historico"
  >("geral");
  const [painel, setPainel] = useState<
    { pergunta_id: string; texto: string; respostas: number; media?: number | null; suprimido?: boolean }[]
  >([]);
  const [ciclos, setCiclos] = useState<Ciclo[]>([]);
  const [cicloAtivo, setCicloAtivo] = useState("");
  const [relacoes, setRelacoes] = useState<Relacao[]>([]);
  const [arvore, setArvore] = useState<NoArvore[]>([]);
  const [pesos, setPesos] = useState(PESOS_PADRAO);
  const [avaliadoResultado, setAvaliadoResultado] = useState("");
  const [notaResultado, setNotaResultado] = useState<{
    resultado: number | null;
    por_perspectiva: Record<string, number>;
  } | null>(null);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [links, setLinks] = useState<string[]>([]);
  const [editando, setEditando] = useState<string | null>(null);
  const [arrasto, setArrasto] = useState<string | null>(null);
  const [midias, setMidias] = useState<Record<string, string>>({});

  function aplicarConfig(config: string | null | undefined) {
    if (!config) {
      setPesos(PESOS_PADRAO);
      return;
    }
    try {
      const dados = JSON.parse(config) as { pesos?: Record<string, number> };
      setPesos({
        AUTO: Number(dados.pesos?.AUTO ?? PESOS_PADRAO.AUTO),
        SUPERIOR: Number(dados.pesos?.SUPERIOR ?? PESOS_PADRAO.SUPERIOR),
        SUBORDINADO: Number(dados.pesos?.SUBORDINADO ?? PESOS_PADRAO.SUBORDINADO),
      });
    } catch {
      setPesos(PESOS_PADRAO);
    }
  }

  const previaPeso = (() => {
    const notas = { AUTO: 4, SUPERIOR: 4.5, SUBORDINADO: 4.2 };
    const soma = pesos.AUTO + pesos.SUPERIOR + pesos.SUBORDINADO;
    if (soma <= 0) return null;
    return (
      Math.round(
        ((notas.AUTO * pesos.AUTO +
          notas.SUPERIOR * pesos.SUPERIOR +
          notas.SUBORDINADO * pesos.SUBORDINADO) /
          soma) *
          100,
      ) / 100
    );
  })();

  const carregar = useCallback(async () => {
    if (!projetoId || !pesquisaId) return;
    setErro("");
    try {
      const lista = await api<Pesquisa[]>(`/projetos/${projetoId}/pesquisas`);
      const atual = lista.find((p) => p.id === pesquisaId) || null;
      setPesquisa(atual);
      const perguntasLista = await api<Pergunta[]>(`/pesquisas/${pesquisaId}/perguntas`);
      setPerguntas([...perguntasLista].sort((a, b) => a.ordem - b.ordem));
      const parts = await api<ParticipantesResp>(
        `/pesquisas/${pesquisaId}/participantes?limite=100`,
      ).catch(() => null);
      if (parts?.agregado) {
        setResumoParticipantes({
          total: parts.total ?? 0,
          respondidas: parts.respondidas ?? 0,
        });
        setParticipantes([]);
        setTotalNominal(0);
      } else {
        setResumoParticipantes(null);
        setParticipantes(parts?.itens || []);
        setTotalNominal(parts?.total ?? 0);
      }
      setArvore(await api<NoArvore[]>(`/projetos/${projetoId}/arvore`).catch(() => []));
      if (atual?.tipo === "DESEMPENHO") {
        const listaCiclos = await api<Ciclo[]>(`/projetos/${projetoId}/ciclos`).catch(
          () => [],
        );
        setCiclos(listaCiclos);
        if (listaCiclos[0]) {
          setCicloAtivo((prev) => prev || listaCiclos[0].id);
          aplicarConfig(listaCiclos[0].configuracao);
        }
      }
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }, [projetoId, pesquisaId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    if (!cicloAtivo) return;
    api<Relacao[]>(`/ciclos/${cicloAtivo}/relacoes`)
      .then(setRelacoes)
      .catch(() => setRelacoes([]));
    const atual = ciclos.find((c) => c.id === cicloAtivo);
    if (atual) aplicarConfig(atual.configuracao);
  }, [cicloAtivo, ciclos]);

  useEffect(() => {
    const comMidia = perguntas.filter((p) => p.tem_midia);
    if (!comMidia.length || !pesquisaId) return;
    let cancel = false;
    const urls: string[] = [];
    void (async () => {
      const mapa: Record<string, string> = {};
      for (const p of comMidia) {
        try {
          const resp = await fetch(
            urlApi(`/pesquisas/${pesquisaId}/perguntas/${p.id}/midia`),
            { headers: { Authorization: `Bearer ${tokenAtual()}` } },
          );
          if (!resp.ok) continue;
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          urls.push(url);
          mapa[p.id] = url;
        } catch {
          /* ignore */
        }
      }
      if (!cancel) setMidias(mapa);
    })();
    return () => {
      cancel = true;
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [perguntas, pesquisaId]);

  async function salvarMeta(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!pesquisa || pesquisa.status !== "RASCUNHO") return;
    setErro("");
    const form = evento.currentTarget;
    try {
      const atualizada = await api<Pesquisa>(`/pesquisas/${pesquisaId}`, {
        method: "PATCH",
        json: {
          titulo: (form.elements.namedItem("titulo") as HTMLInputElement).value,
          descricao: (form.elements.namedItem("descricao") as HTMLInputElement).value || null,
        },
      });
      setPesquisa(atualizada);
      setAviso("Dados salvos.");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function adicionar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!pesquisa || pesquisa.status !== "RASCUNHO") return;
    setErro("");
    const form = evento.currentTarget;
    const tipo = (form.elements.namedItem("tipo") as HTMLSelectElement).value;
    const texto = (form.elements.namedItem("texto") as HTMLInputElement).value;
    const opcoesRaw = (form.elements.namedItem("opcoes") as HTMLInputElement)?.value || "";
    const opcoes =
      tipo === "CHECKBOX" || tipo === "MULTIPLA_ESCOLHA" || tipo === "SIM_NAO"
        ? opcoesRaw
            .split("|")
            .map((t) => t.trim())
            .filter(Boolean)
            .map((t) => ({ texto: t }))
        : [];
    try {
      const criada = await api<Pergunta>(`/pesquisas/${pesquisaId}/perguntas`, {
        method: "POST",
        json: { texto, tipo, obrigatoria: true, opcoes },
      });
      setPerguntas((prev) => [...prev, criada].sort((a, b) => a.ordem - b.ordem));
      form.reset();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function salvarPergunta(p: Pergunta) {
    setErro("");
    try {
      const atualizada = await api<Pergunta>(
        `/pesquisas/${pesquisaId}/perguntas/${p.id}`,
        {
          method: "PATCH",
          json: {
            texto: p.texto,
            tipo: p.tipo,
            obrigatoria: p.obrigatoria,
          },
        },
      );
      setPerguntas((prev) =>
        prev.map((x) => (x.id === p.id ? { ...x, ...atualizada } : x)),
      );
      setEditando(null);
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function excluirPergunta(id: string) {
    setErro("");
    try {
      await api(`/pesquisas/${pesquisaId}/perguntas/${id}`, { method: "DELETE" });
      const lista = await api<Pergunta[]>(`/pesquisas/${pesquisaId}/perguntas`);
      setPerguntas([...lista].sort((a, b) => a.ordem - b.ordem));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function reordenar(ids: string[]) {
    setErro("");
    try {
      await api(`/pesquisas/${pesquisaId}/perguntas/reordenar`, {
        method: "POST",
        json: { pergunta_ids: ids },
      });
      const lista = await api<Pergunta[]>(`/pesquisas/${pesquisaId}/perguntas`);
      setPerguntas([...lista].sort((a, b) => a.ordem - b.ordem));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  function onDrop(alvoId: string) {
    if (!arrasto || arrasto === alvoId || pesquisa?.status !== "RASCUNHO") return;
    const ids = perguntas.map((p) => p.id);
    const de = ids.indexOf(arrasto);
    const para = ids.indexOf(alvoId);
    if (de < 0 || para < 0) return;
    ids.splice(de, 1);
    ids.splice(para, 0, arrasto);
    setArrasto(null);
    void reordenar(ids);
  }

  async function uploadMidia(perguntaId: string, arquivo: File) {
    setErro("");
    const fd = new FormData();
    fd.append("arquivo", arquivo);
    try {
      const atualizada = await api<Pergunta>(
        `/pesquisas/${pesquisaId}/perguntas/${perguntaId}/midia`,
        { method: "POST", formData: fd },
      );
      setPerguntas((prev) => prev.map((p) => (p.id === perguntaId ? atualizada : p)));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro no upload");
    }
  }

  async function removerMidia(perguntaId: string) {
    try {
      const atualizada = await api<Pergunta>(
        `/pesquisas/${pesquisaId}/perguntas/${perguntaId}/midia`,
        { method: "DELETE" },
      );
      setPerguntas((prev) => prev.map((p) => (p.id === perguntaId ? atualizada : p)));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function publicar() {
    setErro("");
    setAviso("");
    try {
      const pub = await api<Pesquisa>(`/pesquisas/${pesquisaId}/publicar`, {
        method: "POST",
      });
      setPesquisa(pub);
      setAviso("Publicada. Gere o link para enviar.");
      const parts = await api<ParticipantesResp>(
        `/pesquisas/${pesquisaId}/participantes?limite=100`,
      );
      if (parts.agregado) {
        setResumoParticipantes({
          total: parts.total ?? 0,
          respondidas: parts.respondidas ?? 0,
        });
        setParticipantes([]);
        setTotalNominal(0);
      } else {
        setResumoParticipantes(null);
        setParticipantes(parts.itens || []);
        setTotalNominal(parts.total ?? 0);
      }
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function gerarLink() {
    setErro("");
    try {
      const resp = await api<{ links: string[]; tokens: string[] }>(
        `/pesquisas/${pesquisaId}/tokens?quantidade=1`,
        { method: "POST" },
      );
      setLinks(resp.links?.length ? resp.links : resp.tokens.map((t) => `/app/responder/${t}`));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function criarCiclo(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    const form = evento.currentTarget;
    try {
      const criado = await api<Ciclo>(`/projetos/${projetoId}/ciclos`, {
        method: "POST",
        json: {
          nome: (form.elements.namedItem("nome") as HTMLInputElement).value,
          escopo: (form.elements.namedItem("escopo") as HTMLSelectElement).value,
          configuracao: JSON.stringify({
            pesos,
            ordem: ["AUTO", "SUPERIOR", "SUBORDINADO"],
            escala: { min: 1, max: 5 },
          }),
        },
      });
      setCiclos((prev) => [criado, ...prev]);
      setCicloAtivo(criado.id);
      setAviso("Ciclo criado.");
      form.reset();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function salvarPesos() {
    if (!cicloAtivo) {
      setErro("Crie um ciclo na aba Regras antes de gravar os pesos.");
      return;
    }
    setErro("");
    try {
      const atualizado = await api<Ciclo>(`/ciclos/${cicloAtivo}`, {
        method: "PATCH",
        json: {
          configuracao: JSON.stringify({
            pesos,
            ordem: ["AUTO", "SUPERIOR", "SUBORDINADO"],
            escala: { min: 1, max: 5 },
          }),
        },
      });
      setCiclos((prev) => prev.map((c) => (c.id === atualizado.id ? atualizado : c)));
      setAviso("Pesos salvos no ciclo.");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function gerarRelacoesCiclo() {
    if (!cicloAtivo) {
      setErro("Crie um ciclo na aba Regras.");
      return;
    }
    setErro("");
    try {
      await api(`/ciclos/${cicloAtivo}/gerar-relacoes`, { method: "POST" });
      setRelacoes(await api<Relacao[]>(`/ciclos/${cicloAtivo}/relacoes`));
      setAviso("Relações geradas a partir da hierarquia.");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  const desempenho = pesquisa?.tipo === "DESEMPENHO";

  const rascunho = pesquisa?.status === "RASCUNHO";

  return (
    <AppShell active="pesquisas">
      <div
        className="mb-4 rounded-3xl px-5 py-4"
        style={{ ...glassStyle, borderLeft: "4px solid #0F766E" }}
      >
        <button
          type="button"
          onClick={() => navigate(`/projetos/${projetoId}`)}
          className="text-[12px] font-semibold mb-2"
          style={{ color: "#0F766E" }}
        >
          ← Voltar ao trabalho
        </button>
        <p className="text-[11px] font-bold uppercase tracking-wide" style={{ color: "#0F766E" }}>
          Edição da pesquisa
        </p>
        <h1 className="text-[18px] font-bold text-gray-800 mt-1">
          {pesquisa?.titulo || "Nova pesquisa"}
        </h1>
        <p className="text-[12px] text-gray-500 mt-1">
          {pesquisa?.tipo || "…"} · {pesquisa?.status || "…"}
        </p>
      </div>
      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}
      {aviso ? <p className="text-[#1E7A4A] text-[13px] mb-3">{aviso}</p> : null}

      <div className="flex flex-wrap gap-2 mb-4">
        {(
          [
            ["geral", "Geral"],
            ["estrutura", "Estrutura"],
            ["perguntas", "Perguntas"],
            ["participantes", "Participantes"],
            ["perspectivas", "Perspectivas"],
            ["pesos", "Pesos"],
            ["regras", "Regras"],
            ["preview", "Prévia"],
            ["aplicacao", "Aplicação"],
            ["resultados", "Resultados"],
            ["historico", "Histórico"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setAba(id)}
            className="px-3 py-1.5 rounded-full text-[12px] font-bold border"
            style={{
              background: aba === id ? "#0F766E" : "rgba(255,255,255,0.55)",
              color: aba === id ? "#fff" : "#0F766E",
              borderColor: aba === id ? "#0F766E" : "rgba(15,118,110,0.25)",
            }}
          >
            {label}
          </button>
        ))}
        {rascunho ? (
          <button
            type="button"
            onClick={() => void publicar()}
            className="ml-auto px-3 py-1.5 rounded-xl text-[12px] font-bold text-white"
            style={{ background: "#1E7A4A" }}
          >
            Publicar
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void gerarLink()}
            className="ml-auto px-3 py-1.5 rounded-xl text-[12px] font-bold text-white"
            style={{ background: ACCENT }}
          >
            Gerar link
          </button>
        )}
      </div>

      {links.length > 0 ? (
        <div className="rounded-2xl p-3 text-[12px] break-all mb-4" style={glassStyle}>
          <p className="font-bold mb-1">Link de resposta</p>
          {links.map((l) => (
            <a key={l} href={l} className="block text-[#1D5FAF] font-semibold underline">
              {l}
            </a>
          ))}
        </div>
      ) : null}

      {aba === "geral" && pesquisa ? (
        <form onSubmit={salvarMeta} className="rounded-3xl p-4 grid gap-3 max-w-lg mb-4" style={glassStyle}>
          <p className="text-[13px] font-bold text-gray-800">Dados da pesquisa</p>
          <label className="text-[12px] font-semibold text-gray-600">
            Nome
            <input name="titulo" defaultValue={pesquisa.titulo} required className={field} disabled={!rascunho} />
          </label>
          <label className="text-[12px] font-semibold text-gray-600">
            Descrição
            <input name="descricao" defaultValue={pesquisa.descricao || ""} className={field} disabled={!rascunho} />
          </label>
          <p className="text-[12px] text-gray-500">Tipo: {pesquisa.tipo}. Status: {pesquisa.status}.</p>
          {rascunho ? (
            <button type="submit" className="rounded-xl py-2.5 text-white text-[13px] font-bold" style={{ background: ACCENT }}>
              Salvar dados
            </button>
          ) : null}
        </form>
      ) : null}

      {aba === "estrutura" && (
        <div className="rounded-3xl p-5" style={glassStyle}>
          <p className="text-[13px] font-bold text-gray-800 mb-2">Hierarquia do trabalho</p>
          <p className="text-[12px] text-gray-500 mb-3">
            A avaliação de desempenho usa esta árvore para gerar AUTO, SUPERIOR e
            SUBORDINADO. Importe a equipe na aba Participantes do trabalho.
          </p>
          <ArvoreOrganizacional arvore={arvore} />
        </div>
      )}

      {aba === "perguntas" && (
        <div className="flex flex-col gap-4">
          {pesquisa && rascunho ? (
            <form onSubmit={salvarMeta} className="rounded-3xl p-4 grid sm:grid-cols-2 gap-3" style={glassStyle}>
              <label className="text-[12px] font-semibold text-gray-600">
                Título
                <input name="titulo" required defaultValue={pesquisa.titulo} className={field} />
              </label>
              <label className="text-[12px] font-semibold text-gray-600">
                Descrição
                <input
                  name="descricao"
                  defaultValue={pesquisa.descricao || ""}
                  className={field}
                />
              </label>
              <button
                type="submit"
                className="sm:col-span-2 self-start rounded-xl px-4 py-2 text-white text-[13px] font-bold"
                style={{ background: ACCENT }}
              >
                Salvar dados
              </button>
            </form>
          ) : null}

          <ul className="flex flex-col gap-2">
            {perguntas.map((p) => (
              <li
                key={p.id}
                draggable={rascunho}
                onDragStart={() => setArrasto(p.id)}
                onDragOver={(e: DragEvent) => e.preventDefault()}
                onDrop={() => onDrop(p.id)}
                className="rounded-2xl p-4"
                style={glassStyle}
              >
                {editando === p.id && rascunho ? (
                  <div className="flex flex-col gap-2">
                    <input
                      className={field}
                      value={p.texto}
                      onChange={(e) =>
                        setPerguntas((prev) =>
                          prev.map((x) =>
                            x.id === p.id ? { ...x, texto: e.target.value } : x,
                          ),
                        )
                      }
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="text-[12px] font-bold text-white px-3 py-1.5 rounded-xl"
                        style={{ background: ACCENT }}
                        onClick={() => void salvarPergunta(p)}
                      >
                        Salvar
                      </button>
                      <button
                        type="button"
                        className="text-[12px] font-bold px-3 py-1.5 rounded-xl"
                        onClick={() => setEditando(null)}
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap justify-between gap-2">
                      <div>
                        <p className="text-[13px] font-semibold">
                          {rascunho ? "⋮⋮ " : ""}
                          {p.ordem}. {p.texto}
                        </p>
                        <p className="text-[11px] text-gray-500">
                          {p.tipo}
                          {p.obrigatoria ? " · obrigatória" : ""}
                          {p.tem_midia ? ` · ${p.midia_tipo}` : ""}
                        </p>
                      </div>
                      {rascunho ? (
                        <div className="flex gap-2 flex-wrap">
                          <button
                            type="button"
                            className="text-[11px] font-bold text-[#1D5FAF]"
                            onClick={() => setEditando(p.id)}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="text-[11px] font-bold text-[#A02828]"
                            onClick={() => void excluirPergunta(p.id)}
                          >
                            Excluir
                          </button>
                        </div>
                      ) : null}
                    </div>
                    {midias[p.id] ? (
                      p.midia_tipo === "VIDEO" ? (
                        <video src={midias[p.id]} controls className="mt-2 max-h-40 rounded-xl" />
                      ) : (
                        <img
                          src={midias[p.id]}
                          alt=""
                          className="mt-2 max-h-40 rounded-xl object-contain"
                        />
                      )
                    ) : null}
                    {rascunho ? (
                      <div className="mt-2 flex flex-wrap gap-2 items-center">
                        <label className="text-[11px] font-semibold text-gray-600 cursor-pointer">
                          Anexar foto/vídeo
                          <input
                            type="file"
                            accept="image/*,video/*"
                            className="hidden"
                            onChange={(e) => {
                              const f = e.target.files?.[0];
                              if (f) void uploadMidia(p.id, f);
                            }}
                          />
                        </label>
                        {p.tem_midia ? (
                          <button
                            type="button"
                            className="text-[11px] font-bold text-[#A02828]"
                            onClick={() => void removerMidia(p.id)}
                          >
                            Remover mídia
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </>
                )}
              </li>
            ))}
          </ul>

          {rascunho ? (
            <form onSubmit={adicionar} className="rounded-3xl p-4 grid sm:grid-cols-2 gap-3" style={glassStyle}>
              <label className="text-[12px] font-semibold text-gray-600 sm:col-span-2">
                Nova pergunta
                <input name="texto" required minLength={2} className={field} />
              </label>
              <label className="text-[12px] font-semibold text-gray-600">
                Tipo
                <select name="tipo" className={field} defaultValue="NOTA_5">
                  <option value="NOTA_5">Nota 1–5</option>
                  <option value="NOTA_10">Nota 1–10</option>
                  <option value="TEXTO_LIVRE">Texto livre</option>
                  <option value="SIM_NAO">Sim / Não</option>
                  <option value="MULTIPLA_ESCOLHA">Múltipla escolha</option>
                  <option value="CHECKBOX">Checkbox (várias)</option>
                </select>
              </label>
              <label className="text-[12px] font-semibold text-gray-600">
                Opções (separadas por |)
                <input name="opcoes" placeholder="Sim|Não|Talvez" className={field} />
              </label>
              <button
                type="submit"
                className="sm:col-span-2 rounded-xl py-2.5 text-white text-[13px] font-bold"
                style={{ background: ACCENT }}
              >
                Adicionar pergunta
              </button>
            </form>
          ) : null}
        </div>
      )}

      {aba === "participantes" && (
        <div className="rounded-3xl p-5" style={glassStyle}>
          {resumoParticipantes ? (
            <>
              <p className="text-[12px] text-gray-500 mb-3">
                Pesquisa de clima: só totais — sem nome, e-mail ou status individual.
              </p>
              <p className="text-[14px] font-semibold text-gray-800">
                {resumoParticipantes.respondidas} de {resumoParticipantes.total}{" "}
                respostas
              </p>
            </>
          ) : (
            <>
              <p className="text-[12px] text-gray-500 mb-3">
                Status de cada funcionário — sem conteúdo das respostas.
              </p>
              <ul className="flex flex-col gap-2">
                {participantes.map((p) => (
                  <li
                    key={p.usuario_id}
                    className="p-3 rounded-2xl flex justify-between gap-2"
                    style={{ background: "rgba(255,255,255,0.55)" }}
                  >
                    <div>
                      <p className="text-[13px] font-semibold">{p.nome}</p>
                      <p className="text-[11px] text-gray-500">{p.email}</p>
                    </div>
                    <span className="text-[12px] font-bold text-[#1D5FAF]">{p.status}</span>
                  </li>
                ))}
                {participantes.length === 0 ? (
                  <p className="text-gray-500 text-[13px]">
                    Nenhum funcionário no projeto ainda. Convide na aba Equipe.
                  </p>
                ) : null}
                {participantes.length < totalNominal ? (
                  <button
                    type="button"
                    className="text-[12px] font-bold text-left"
                    style={{ color: "#0F766E" }}
                    onClick={() =>
                      void api<ParticipantesResp>(
                        `/pesquisas/${pesquisaId}/participantes?limite=100&deslocamento=${participantes.length}`,
                      ).then((pagina) => {
                        setParticipantes((atual) => [...atual, ...(pagina.itens || [])]);
                      })
                    }
                  >
                    Carregar mais
                  </button>
                ) : null}
              </ul>
            </>
          )}
        </div>
      )}

      {aba === "preview" && (
        <div className="rounded-3xl p-5" style={glassStyle}>
          <p className="text-[12px] text-gray-500 mb-4">
            Como o funcionário verá (somente leitura — não grava resposta).
          </p>
          <ol className="flex flex-col gap-4">
            {perguntas.map((p, i) => (
              <li key={p.id}>
                <p className="text-[13px] font-semibold mb-1">
                  {i + 1}. {p.texto}
                  {p.obrigatoria ? " *" : ""}
                </p>
                {midias[p.id] ? (
                  p.midia_tipo === "VIDEO" ? (
                    <video src={midias[p.id]} controls className="max-h-40 rounded-xl mb-2" />
                  ) : (
                    <img
                      src={midias[p.id]}
                      alt=""
                      className="max-h-40 rounded-xl object-contain mb-2"
                    />
                  )
                ) : null}
                <p className="text-[11px] text-gray-500">{p.tipo}</p>
              </li>
            ))}
            {perguntas.length === 0 ? (
              <p className="text-gray-500 text-[13px]">Sem perguntas.</p>
            ) : null}
          </ol>
          {desempenho ? (
            <div className="mt-5 rounded-2xl p-4" style={{ background: "rgba(15,118,110,0.08)" }}>
              <p className="text-[13px] font-bold text-gray-800 mb-1">Prévia do cálculo</p>
              <p className="text-[12px] text-gray-600">
                Exemplo com notas AUTO 4,0 × {pesos.AUTO} + SUPERIOR 4,5 × {pesos.SUPERIOR}{" "}
                + SUBORDINADO 4,2 × {pesos.SUBORDINADO}
                {previaPeso != null ? ` → ${previaPeso}` : "."}
              </p>
            </div>
          ) : null}
          <Link
            to={`/projetos/${projetoId}`}
            className="inline-block mt-4 text-[12px] font-bold text-[#1D5FAF]"
          >
            Voltar ao trabalho
          </Link>
        </div>
      )}

      {aba === "aplicacao" && (
        <div className="rounded-3xl p-5 max-w-lg" style={glassStyle}>
          <p className="text-[13px] text-gray-700 mb-3">
            Publicar abre a pesquisa para quem já está no trabalho e envia o aviso.
            O rascunho precisa de ao menos uma pergunta e das pesquisas ligadas na configuração.
          </p>
          <p className="text-[12px] text-gray-500 mb-4">
            Status atual: <strong>{pesquisa?.status || "…"}</strong>
          </p>
          {rascunho ? (
            <button
              type="button"
              onClick={() => void publicar()}
              className="rounded-xl px-4 py-2.5 text-white text-[13px] font-bold"
              style={{ background: "#1E7A4A" }}
            >
              Publicar pesquisa
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void gerarLink()}
              className="rounded-xl px-4 py-2.5 text-white text-[13px] font-bold"
              style={{ background: ACCENT }}
            >
              Gerar link de resposta
            </button>
          )}
        </div>
      )}

      {aba === "perspectivas" && (
        <div className="rounded-3xl p-5 max-w-2xl" style={glassStyle}>
          {desempenho ? (
            <>
              <p className="text-[13px] font-bold text-gray-800 mb-2">Perspectivas do ciclo</p>
              <p className="text-[12px] text-gray-500 mb-3">
                AUTO, SUPERIOR e SUBORDINADO saem da hierarquia. Sem superior, não
                cria SUPERIOR. Sem subordinado, não cria SUBORDINADO.
              </p>
              {ciclos.length > 0 ? (
                <label className="text-[12px] font-semibold text-gray-600 block mb-3">
                  Ciclo
                  <select
                    className={field}
                    value={cicloAtivo}
                    onChange={(e) => setCicloAtivo(e.target.value)}
                  >
                    {ciclos.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome} · {c.status}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p className="text-[12px] text-gray-500 mb-3">
                  Nenhum ciclo. Crie um na aba Regras.
                </p>
              )}
              <ul className="flex flex-col gap-2">
                {relacoes.map((r) => (
                  <li
                    key={r.id}
                    className="p-3 rounded-2xl text-[12px]"
                    style={{ background: "rgba(255,255,255,0.55)" }}
                  >
                    <span className="font-bold">{r.tipo_relacao}</span>
                    {" · "}
                    {r.avaliador_nome || r.avaliador_id} avalia{" "}
                    {r.avaliado_nome || r.avaliado_id}
                    {" · peso "}
                    {r.peso} · {r.status}
                  </li>
                ))}
                {relacoes.length === 0 ? (
                  <p className="text-gray-500 text-[13px]">Nenhuma relação gerada ainda.</p>
                ) : null}
              </ul>
              <button
                type="button"
                onClick={() => void gerarRelacoesCiclo()}
                className="mt-3 rounded-xl px-4 py-2 text-white text-[12px] font-bold"
                style={{ background: ACCENT }}
              >
                Gerar relações
              </button>
            </>
          ) : (
            <p className="text-[13px] text-gray-600">
              Perspectivas valem só para avaliação de desempenho.
            </p>
          )}
        </div>
      )}

      {aba === "pesos" && (
        <div className="rounded-3xl p-5 max-w-lg" style={glassStyle}>
          {desempenho ? (
            <>
              <p className="text-[13px] font-bold text-gray-800 mb-2">Pesos do ciclo</p>
              <p className="text-[12px] text-gray-500 mb-3">
                Números, nunca código. O resultado é a média ponderada das
                perspectivas que tiverem nota.
              </p>
              {(
                [
                  ["AUTO", "Autoavaliação"],
                  ["SUPERIOR", "Superior"],
                  ["SUBORDINADO", "Subordinados"],
                ] as const
              ).map(([chave, label]) => (
                <label key={chave} className="text-[12px] font-semibold text-gray-600 block mb-3">
                  {label} ({chave})
                  <input
                    type="number"
                    min={0}
                    max={10}
                    step={0.5}
                    className={field}
                    value={pesos[chave]}
                    onChange={(e) =>
                      setPesos((prev) => ({
                        ...prev,
                        [chave]: Number(e.target.value),
                      }))
                    }
                  />
                </label>
              ))}
              <p className="text-[12px] text-gray-600 mb-3">
                Exemplo: AUTO 4,0×{pesos.AUTO} + SUPERIOR 4,5×{pesos.SUPERIOR} +
                SUBORDINADO 4,2×{pesos.SUBORDINADO}
                {previaPeso != null ? ` → ${previaPeso}` : "."}
              </p>
              <button
                type="button"
                onClick={() => void salvarPesos()}
                className="rounded-xl px-4 py-2 text-white text-[12px] font-bold"
                style={{ background: ACCENT }}
              >
                Salvar pesos
              </button>
            </>
          ) : (
            <p className="text-[13px] text-gray-600">
              Pesos valem só para avaliação de desempenho.
            </p>
          )}
        </div>
      )}

      {aba === "regras" && (
        <div className="rounded-3xl p-5 max-w-lg" style={glassStyle}>
          {desempenho ? (
            <>
              <p className="text-[13px] font-bold text-gray-800 mb-2">Regras do ciclo</p>
              <p className="text-[12px] text-gray-500 mb-3">
                O ciclo trava escopo e pesos. Depois de publicado, mudança
                estrutural exige um ciclo novo.
              </p>
              <form onSubmit={criarCiclo} className="grid gap-3">
                <label className="text-[12px] font-semibold text-gray-600">
                  Nome do ciclo
                  <input name="nome" required minLength={2} className={field} placeholder="Avaliação 2026" />
                </label>
                <label className="text-[12px] font-semibold text-gray-600">
                  Escopo
                  <select name="escopo" className={field} defaultValue="ORGANIZACAO">
                    <option value="ORGANIZACAO">Organização</option>
                    <option value="SETOR">Setor</option>
                    <option value="CARGO">Cargo</option>
                    <option value="MANUAL">Manual</option>
                  </select>
                </label>
                <button
                  type="submit"
                  className="rounded-xl py-2.5 text-white text-[13px] font-bold"
                  style={{ background: ACCENT }}
                >
                  Criar ciclo
                </button>
              </form>
            </>
          ) : (
            <p className="text-[13px] text-gray-600">
              Ciclos e regras valem só para avaliação de desempenho.
            </p>
          )}
        </div>
      )}

      {aba === "historico" && (
        <div className="rounded-3xl p-5" style={glassStyle}>
          <p className="text-[13px] text-gray-600">
            {desempenho ? "Ciclos deste trabalho." : "Histórico desta pesquisa."}
          </p>
          <ul className="flex flex-col gap-2 mt-3">
            {ciclos.map((c) => (
              <li
                key={c.id}
                className="p-3 rounded-2xl text-[12px] flex justify-between gap-2"
                style={{ background: "rgba(255,255,255,0.55)" }}
              >
                <span>
                  {c.nome} · {c.escopo} · {c.status}
                </span>
                <button
                  type="button"
                  className="text-[11px] font-bold"
                  style={{ color: ACCENT }}
                  onClick={() => {
                    setCicloAtivo(c.id);
                    setAba("perspectivas");
                  }}
                >
                  Abrir
                </button>
              </li>
            ))}
            {ciclos.length === 0 ? (
              <p className="text-gray-500 text-[13px]">
                {desempenho ? "Nenhum ciclo ainda." : "Sem ciclos — tipo não usa ciclo."}
              </p>
            ) : null}
          </ul>
        </div>
      )}

      {aba === "resultados" && (
        <div className="rounded-3xl p-5" style={glassStyle}>
          <button
            type="button"
            className="rounded-xl px-4 py-2 text-white text-[12px] font-bold mb-3"
            style={{ background: ACCENT }}
            onClick={() =>
              void api<typeof painel>(`/pesquisas/${pesquisaId}/painel`)
                .then(setPainel)
                .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"))
            }
          >
            Carregar consolidado
          </button>
          {painel.map((item) => (
            <p key={item.pergunta_id} className="text-[12px] text-gray-600 mb-1">
              {item.texto} · {item.respostas} respostas
              {item.suprimido ? " · oculto (poucas respostas)" : ""}
              {item.media != null ? ` · média ${item.media}` : ""}
            </p>
          ))}
          {desempenho && cicloAtivo ? (
            <div className="mt-4 pt-3" style={{ borderTop: "1px solid rgba(0,0,0,0.06)" }}>
              <p className="text-[13px] font-bold text-gray-800 mb-2">Nota ponderada</p>
              <label className="text-[12px] font-semibold text-gray-600 block mb-2">
                Avaliado
                <select
                  className={field}
                  value={avaliadoResultado}
                  onChange={(e) => setAvaliadoResultado(e.target.value)}
                >
                  <option value="">Selecione</option>
                  {[...new Set(relacoes.map((r) => r.avaliado_id))].map((uid) => {
                    const nome =
                      relacoes.find((r) => r.avaliado_id === uid)?.avaliado_nome || uid;
                    return (
                      <option key={uid} value={uid}>
                        {nome}
                      </option>
                    );
                  })}
                </select>
              </label>
              <button
                type="button"
                disabled={!avaliadoResultado}
                className="rounded-xl px-4 py-2 text-white text-[12px] font-bold disabled:opacity-60"
                style={{ background: "#0F766E" }}
                onClick={() =>
                  void api<typeof notaResultado>(
                    `/ciclos/${cicloAtivo}/resultado/${avaliadoResultado}`,
                  )
                    .then(setNotaResultado)
                    .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"))
                }
              >
                Calcular
              </button>
              {notaResultado ? (
                <p className="text-[12px] text-gray-600 mt-2">
                  Resultado: {notaResultado.resultado ?? "sem notas ainda"}
                  {Object.entries(notaResultado.por_perspectiva || {}).map(
                    ([tipo, nota]) => ` · ${tipo} ${nota}`,
                  )}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      )}
    </AppShell>
  );
}
