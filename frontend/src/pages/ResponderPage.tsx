import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api, tokenAtual, urlApi } from "../lib/api";
import { ACCENT, glassStyle } from "../lib/theme";

const RETORNO_KEY = "horizon_responder_retorno";

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
type NotaSaida = { tipo: string; mensagem: string; nota: number | null };

export function guardarRetornoResponder(caminho: string) {
  sessionStorage.setItem(RETORNO_KEY, caminho);
}

export function consumirRetornoResponder(): string | null {
  const v = sessionStorage.getItem(RETORNO_KEY);
  if (v) sessionStorage.removeItem(RETORNO_KEY);
  return v;
}

/**
 * Resposta autenticada. Sem login → guarda o link e manda para /entrar.
 * Papel errado → mensagem fixa, sem mostrar perguntas.
 * Minhas pesquisas: /responder/pesquisa/:id (sem token no URL).
 * Link da consultora: /responder/:token.
 */
export function ResponderPage() {
  const { token: tokenRota, pesquisaId: pesquisaRota } = useParams();
  const pesquisaId = (pesquisaRota || "").trim();
  const token =
    pesquisaId
      ? ""
      : (tokenRota || "").trim() ||
        decodeURIComponent(window.location.hash.replace(/^#/, "")).trim();
  const modoPesquisa = Boolean(pesquisaId);
  const baseApi = modoPesquisa
    ? `/eu/pesquisas/${encodeURIComponent(pesquisaId)}`
    : `/responder/${encodeURIComponent(token)}`;
  const caminhoRetorno = modoPesquisa
    ? `/responder/pesquisa/${encodeURIComponent(pesquisaId)}`
    : `/responder/${encodeURIComponent(token)}`;
  const { pronto, usuario } = useAuth();
  const navigate = useNavigate();

  const [perguntas, setPerguntas] = useState<Pergunta[]>([]);
  const [indice, setIndice] = useState(0);
  const [erro, setErro] = useState("");
  const [reservado, setReservado] = useState(false);
  const [ok, setOk] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [respostas, setRespostas] = useState<Record<string, unknown>>({});
  const [midias, setMidias] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!pronto) return;
    if (!modoPesquisa && !token) {
      setErro("Abra o link completo que a consultora enviou.");
      setCarregando(false);
      return;
    }
    if (!usuario) {
      guardarRetornoResponder(caminhoRetorno);
      navigate("/entrar", { replace: true });
      return;
    }
    setCarregando(true);
    setErro("");
    setReservado(false);
    const caminho = modoPesquisa ? `${baseApi}/formulario` : baseApi;
    // #region agent log
    fetch("http://127.0.0.1:7496/ingest/74f2214c-a2bc-4cc8-ac4b-5ae97a5b0219", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Debug-Session-Id": "6ef563",
      },
      body: JSON.stringify({
        sessionId: "6ef563",
        runId: "post-pages",
        hypothesisId: "H4",
        location: "ResponderPage.tsx:load",
        message: "opening formulario",
        data: {
          host: window.location.host,
          modoPesquisa,
          temPesquisaId: Boolean(pesquisaId),
          temToken: Boolean(token),
          caminho,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
    api<Pergunta[]>(caminho)
      .then((lista) => {
        // #region agent log
        fetch("http://127.0.0.1:7496/ingest/74f2214c-a2bc-4cc8-ac4b-5ae97a5b0219", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Debug-Session-Id": "6ef563",
          },
          body: JSON.stringify({
            sessionId: "6ef563",
            runId: "post-pages",
            hypothesisId: "H4",
            location: "ResponderPage.tsx:ok",
            message: "formulario ok",
            data: { host: window.location.host, perguntas: lista.length },
            timestamp: Date.now(),
          }),
        }).catch(() => {});
        // #endregion
        const ordenada = [...lista].sort((a, b) => a.ordem - b.ordem);
        setPerguntas(ordenada);
        setIndice(0);
      })
      .catch((exc) => {
        const msg = exc instanceof Error ? exc.message : "Erro";
        // #region agent log
        fetch("http://127.0.0.1:7496/ingest/74f2214c-a2bc-4cc8-ac4b-5ae97a5b0219", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Debug-Session-Id": "6ef563",
          },
          body: JSON.stringify({
            sessionId: "6ef563",
            runId: "post-pages",
            hypothesisId: "H4",
            location: "ResponderPage.tsx:err",
            message: "formulario erro",
            data: { host: window.location.host, msg: String(msg).slice(0, 120) },
            timestamp: Date.now(),
          }),
        }).catch(() => {});
        // #endregion
        if (
          usuario.painel !== "funcionario" ||
          /não encontrad|inválido|já usado|Link/i.test(msg)
        ) {
          setReservado(true);
          setErro("Reservado a funcionários deste projeto");
        } else {
          setErro(msg);
        }
      })
      .finally(() => setCarregando(false));
  }, [pronto, usuario, token, pesquisaId, modoPesquisa, baseApi, caminhoRetorno, navigate]);

  useEffect(() => {
    const atuais = perguntas.filter((p) => p.tem_midia);
    if (!atuais.length || (!token && !pesquisaId)) return;
    let cancelado = false;
    const urls: string[] = [];
    void (async () => {
      const mapa: Record<string, string> = {};
      for (const p of atuais) {
        try {
          const resp = await fetch(
            urlApi(`${baseApi}/perguntas/${p.id}/midia`),
            { headers: { Authorization: `Bearer ${tokenAtual()}` } },
          );
          if (!resp.ok) continue;
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          urls.push(url);
          mapa[p.id] = url;
        } catch {
          /* preview opcional */
        }
      }
      if (!cancelado) setMidias(mapa);
    })();
    return () => {
      cancelado = true;
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [perguntas, token, pesquisaId, baseApi]);

  const atual = perguntas[indice];
  const total = perguntas.length;
  const progresso = useMemo(
    () => (total ? Math.round(((indice + 1) / total) * 100) : 0),
    [indice, total],
  );

  function validarObrigatorias(): string | null {
    for (const item of perguntas) {
      if (!item.obrigatoria) continue;
      const valor = respostas[item.id];
      if (item.tipo === "CHECKBOX") {
        if (!Array.isArray(valor) || valor.length === 0) {
          return `Responda: ${item.texto}`;
        }
        continue;
      }
      if (item.tipo === "TEXTO_LIVRE") {
        if (!String(valor || "").trim()) return `Responda: ${item.texto}`;
        continue;
      }
      if (valor === undefined || valor === null || valor === "") {
        return `Responda: ${item.texto}`;
      }
    }
    return null;
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!modoPesquisa && !token) return;
    const falta = validarObrigatorias();
    if (falta) {
      setErro(falta);
      return;
    }
    setErro("");
    setOk("");
    const payload: {
      pergunta_id: string;
      valor_texto?: string | null;
      valor_numerico?: number | null;
      opcao_id?: string | null;
      opcao_ids?: string[];
    }[] = [];

    for (const item of perguntas) {
      const valor = respostas[item.id];
      if (item.tipo === "TEXTO_LIVRE") {
        payload.push({ pergunta_id: item.id, valor_texto: String(valor || "") });
        continue;
      }
      if (item.tipo === "NOTA_5" || item.tipo === "NOTA_10") {
        payload.push({
          pergunta_id: item.id,
          valor_numerico: valor === "" || valor == null ? null : Number(valor),
        });
        continue;
      }
      if (item.tipo === "CHECKBOX") {
        const ids = Array.isArray(valor) ? (valor as string[]) : [];
        payload.push({
          pergunta_id: item.id,
          opcao_ids: ids,
          opcao_id: null,
        });
        continue;
      }
      payload.push({
        pergunta_id: item.id,
        opcao_id: valor ? String(valor) : null,
      });
    }

    try {
      const destino = modoPesquisa ? `${baseApi}/responder` : baseApi;
      const saida = await api<NotaSaida>(destino, {
        method: "POST",
        json: { respostas: payload },
      });
      setEnviado(true);
      if (saida.tipo === "DESEMPENHO" && saida.nota != null) {
        setOk(`${saida.mensagem} Sua nota: ${saida.nota}.`);
      } else {
        setOk(saida.mensagem || "Resposta registrada.");
      }
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro ao enviar");
    }
  }

  if (!pronto || carregando) {
    return (
      <div className="min-h-screen page-bg flex items-center justify-center text-gray-500 text-sm">
        Carregando…
      </div>
    );
  }

  if (reservado) {
    return (
      <div className="min-h-screen page-bg flex items-center justify-center px-4">
        <div className="max-w-md w-full rounded-3xl p-6 text-center" style={glassStyle}>
          <h1 className="text-[18px] font-bold text-gray-800 mb-2">Acesso restrito</h1>
          <p className="text-[13px] text-gray-600 mb-4">{erro}</p>
          <Link
            to="/inicio"
            className="inline-block rounded-xl px-4 py-2.5 text-white text-[13px] font-bold"
            style={{ background: ACCENT }}
          >
            Ir ao meu painel
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen page-bg px-3 py-8 flex justify-center">
      <div className="w-full max-w-lg rounded-3xl p-5 sm:p-6" style={glassStyle}>
        <h1 className="text-[20px] font-bold text-gray-800 mb-1">Responder pesquisa</h1>
        <p className="text-[12px] text-gray-500 mb-4">
          Suas respostas individuais não aparecem no painel do órgão.
        </p>
        {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}
        {ok ? <p className="text-[#1E7A4A] text-[13px] mb-3">{ok}</p> : null}

        {enviado ? (
          <Link to="/inicio" className="text-[13px] font-bold text-[#1D5FAF]">
            Voltar ao início
          </Link>
        ) : total === 0 ? (
          <p className="text-gray-500 text-[13px]">Nenhuma pergunta nesta pesquisa.</p>
        ) : (
          <form onSubmit={enviar} className="flex flex-col gap-4">
            <div>
              <div className="flex justify-between text-[11px] text-gray-500 mb-1">
                <span>
                  Pergunta {indice + 1} de {total}
                </span>
                <span>{progresso}%</span>
              </div>
              <div className="h-2 rounded-full bg-white/60 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${progresso}%`, background: ACCENT }}
                />
              </div>
            </div>

            {atual ? (
              <fieldset className="flex flex-col gap-3">
                <legend className="text-[14px] font-semibold text-gray-800">
                  {atual.texto}
                  {atual.obrigatoria ? (
                    <span className="text-[#A02828] ml-1">*</span>
                  ) : null}
                </legend>
                {midias[atual.id] ? (
                  atual.midia_tipo === "VIDEO" ? (
                    <video
                      src={midias[atual.id]}
                      controls
                      className="w-full rounded-2xl max-h-56 bg-black"
                    />
                  ) : (
                    <img
                      src={midias[atual.id]}
                      alt=""
                      className="w-full rounded-2xl max-h-56 object-contain bg-white/40"
                    />
                  )
                ) : null}
                <CampoPergunta
                  pergunta={atual}
                  valor={respostas[atual.id]}
                  onChange={(v) =>
                    setRespostas((prev) => ({ ...prev, [atual.id]: v }))
                  }
                />
              </fieldset>
            ) : null}

            <div className="flex flex-wrap gap-2 justify-between mt-2">
              <button
                type="button"
                disabled={indice === 0}
                onClick={() => setIndice((i) => Math.max(0, i - 1))}
                className="rounded-xl px-4 py-2.5 text-[13px] font-bold disabled:opacity-40"
                style={{ background: "rgba(255,255,255,0.7)" }}
              >
                Anterior
              </button>
              {indice < total - 1 ? (
                <button
                  type="button"
                  onClick={() => setIndice((i) => Math.min(total - 1, i + 1))}
                  className="rounded-xl px-4 py-2.5 text-white text-[13px] font-bold"
                  style={{ background: ACCENT }}
                >
                  Próxima
                </button>
              ) : (
                <button
                  type="submit"
                  className="rounded-xl px-4 py-2.5 text-white text-[13px] font-bold"
                  style={{ background: "#1E7A4A" }}
                >
                  Enviar respostas
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function CampoPergunta({
  pergunta,
  valor,
  onChange,
}: {
  pergunta: Pergunta;
  valor: unknown;
  onChange: (v: unknown) => void;
}) {
  const field =
    "mt-1 w-full rounded-xl px-3 py-2.5 text-[13px] outline-none bg-white/70 border border-white/80";

  if (pergunta.tipo === "TEXTO_LIVRE") {
    return (
      <textarea
        className={field}
        rows={3}
        value={String(valor || "")}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  if (pergunta.tipo === "NOTA_5" || pergunta.tipo === "NOTA_10") {
    const max = pergunta.tipo === "NOTA_5" ? 5 : 10;
    return (
      <select
        className={field}
        value={valor == null ? "" : String(valor)}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}
      >
        <option value="">Selecione</option>
        {Array.from({ length: max }, (_, i) => i + 1).map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    );
  }
  if (pergunta.tipo === "CHECKBOX") {
    const marcadas = Array.isArray(valor) ? (valor as string[]) : [];
    return (
      <div className="flex flex-col gap-2">
        {pergunta.opcoes.map((op) => {
          const checked = marcadas.includes(op.id);
          return (
            <label key={op.id} className="flex items-center gap-2 text-[13px]">
              <input
                type="checkbox"
                checked={checked}
                onChange={() => {
                  onChange(
                    checked
                      ? marcadas.filter((id) => id !== op.id)
                      : [...marcadas, op.id],
                  );
                }}
              />
              {op.texto}
            </label>
          );
        })}
      </div>
    );
  }
  // SIM_NAO / MULTIPLA_ESCOLHA
  return (
    <div className="flex flex-col gap-2">
      {pergunta.opcoes.map((op) => (
        <label key={op.id} className="flex items-center gap-2 text-[13px]">
          <input
            type="radio"
            name={pergunta.id}
            checked={valor === op.id}
            onChange={() => onChange(op.id)}
          />
          {op.texto}
        </label>
      ))}
    </div>
  );
}
