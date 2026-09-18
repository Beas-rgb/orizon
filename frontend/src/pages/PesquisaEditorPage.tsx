import { useCallback, useEffect, useState, type DragEvent, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { api, tokenAtual, urlApi } from "../lib/api";
import { ACCENT, glassStyle } from "../lib/theme";

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
  const [aba, setAba] = useState<"perguntas" | "participantes" | "preview">("perguntas");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [links, setLinks] = useState<string[]>([]);
  const [editando, setEditando] = useState<string | null>(null);
  const [arrasto, setArrasto] = useState<string | null>(null);
  const [midias, setMidias] = useState<Record<string, string>>({});

  const carregar = useCallback(async () => {
    if (!projetoId || !pesquisaId) return;
    setErro("");
    try {
      const lista = await api<Pesquisa[]>(`/projetos/${projetoId}/pesquisas`);
      setPesquisa(lista.find((p) => p.id === pesquisaId) || null);
      const perguntasLista = await api<Pergunta[]>(`/pesquisas/${pesquisaId}/perguntas`);
      setPerguntas([...perguntasLista].sort((a, b) => a.ordem - b.ordem));
      setParticipantes(
        await api<Participante[]>(`/pesquisas/${pesquisaId}/participantes`).catch(
          () => [],
        ),
      );
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }, [projetoId, pesquisaId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

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
      setParticipantes(
        await api<Participante[]>(`/pesquisas/${pesquisaId}/participantes`),
      );
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

  const rascunho = pesquisa?.status === "RASCUNHO";

  return (
    <AppShell active="pesquisas">
      <div className="mb-4">
        <button
          type="button"
          onClick={() => navigate(`/projetos/${projetoId}`)}
          className="text-[12px] text-[#1D5FAF] font-semibold mb-2"
        >
          ← Voltar ao projeto
        </button>
        <h1 className="text-[18px] font-bold text-gray-800">
          {pesquisa?.titulo || "Editor de pesquisa"}
        </h1>
        <p className="text-[12px] text-gray-500">
          {pesquisa?.tipo} · {pesquisa?.status || "…"}
        </p>
      </div>
      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}
      {aviso ? <p className="text-[#1E7A4A] text-[13px] mb-3">{aviso}</p> : null}

      <div className="flex flex-wrap gap-2 mb-4">
        {(
          [
            ["perguntas", "Perguntas"],
            ["participantes", "Participantes"],
            ["preview", "Preview"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setAba(id)}
            className="px-3 py-1.5 rounded-xl text-[12px] font-bold"
            style={{
              background: aba === id ? ACCENT : "rgba(255,255,255,0.7)",
              color: aba === id ? "#fff" : "#334",
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
          </ul>
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
          <Link
            to={`/projetos/${projetoId}`}
            className="inline-block mt-4 text-[12px] font-bold text-[#1D5FAF]"
          >
            Voltar
          </Link>
        </div>
      )}
    </AppShell>
  );
}
