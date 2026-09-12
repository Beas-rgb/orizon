import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { ACCENT, glassStyle } from "../lib/theme";

type Opcao = { id: string; texto: string; ordem?: number };
type Pergunta = {
  id: string;
  texto: string;
  tipo: string;
  obrigatoria: boolean;
  ordem: number;
  opcoes: Opcao[];
};
type NotaSaida = { tipo: string; mensagem: string; nota: number | null };

/**
 * Página pública: responde pesquisa só com o token do link.
 * Sem login — o backend valida o token (uso único, validade).
 */
export function ResponderPage() {
  const { token: tokenRota } = useParams();
  const token =
    (tokenRota || "").trim() ||
    decodeURIComponent(window.location.hash.replace(/^#/, "")).trim();

  const [perguntas, setPerguntas] = useState<Pergunta[]>([]);
  const [erro, setErro] = useState("");
  const [ok, setOk] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (!token) {
      setErro("Abra o link completo que a consultora enviou.");
      setCarregando(false);
      return;
    }
    api<Pergunta[]>(`/responder/${encodeURIComponent(token)}`)
      .then(setPerguntas)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"))
      .finally(() => setCarregando(false));
  }, [token]);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!token) return;
    setErro("");
    setOk("");
    const form = evento.currentTarget;
    const respostas: {
      pergunta_id: string;
      valor_texto?: string | null;
      valor_numerico?: number | null;
      opcao_id?: string | null;
    }[] = [];

    for (const item of perguntas) {
      if (item.tipo === "TEXTO_LIVRE") {
        const campo = form.elements.namedItem(item.id) as HTMLTextAreaElement | null;
        respostas.push({ pergunta_id: item.id, valor_texto: campo?.value || "" });
        continue;
      }
      if (item.tipo === "NOTA_5" || item.tipo === "NOTA_10") {
        const campo = form.elements.namedItem(item.id) as HTMLSelectElement | null;
        const valor = campo?.value ? Number(campo.value) : null;
        respostas.push({ pergunta_id: item.id, valor_numerico: valor });
        continue;
      }
      if (item.tipo === "CHECKBOX") {
        const marcadas = form.querySelectorAll<HTMLInputElement>(
          `input[name="${item.id}"]:checked`,
        );
        if (!marcadas.length) {
          respostas.push({ pergunta_id: item.id, opcao_id: null });
        } else {
          marcadas.forEach((input) => {
            respostas.push({ pergunta_id: item.id, opcao_id: input.value });
          });
        }
        continue;
      }
      const marcada = form.querySelector<HTMLInputElement>(
        `input[name="${item.id}"]:checked`,
      );
      respostas.push({
        pergunta_id: item.id,
        opcao_id: marcada ? marcada.value : null,
      });
    }

    try {
      const saida = await api<NotaSaida>(`/responder/${encodeURIComponent(token)}`, {
        method: "POST",
        json: { respostas },
      });
      setEnviado(true);
      if (saida.tipo === "DESEMPENHO" && saida.nota != null) {
        setOk(`${saida.mensagem} Sua nota: ${saida.nota}.`);
      } else {
        setOk(saida.mensagem);
      }
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro ao enviar");
    }
  }

  const field =
    "mt-1 w-full rounded-xl px-3 py-2.5 outline-none bg-white/70 border border-white/80 text-[13px]";

  return (
    <div className="min-h-screen page-bg flex items-center justify-center p-4">
      <div className="w-full max-w-lg rounded-3xl p-6" style={glassStyle}>
        <p className="text-[11px] font-bold tracking-wide text-[#1D5FAF] mb-1">HORIZON</p>
        <h1 className="text-[20px] font-bold text-gray-800 mb-1">Responder pesquisa</h1>
        <p className="text-[12px] text-gray-500 mb-4">
          Link anônimo. Em clima, sua identidade não aparece. O link só funciona uma vez.
        </p>
        {carregando ? <p className="text-[13px] text-gray-500">Carregando…</p> : null}
        {erro ? <p className="text-[13px] text-[#A02828] mb-3">{erro}</p> : null}
        {ok ? <p className="text-[13px] text-[#1E7A4A] mb-3">{ok}</p> : null}
        {!carregando && !enviado && perguntas.length > 0 ? (
          <form onSubmit={enviar} className="flex flex-col gap-4">
            {perguntas.map((item) => (
              <fieldset key={item.id} className="text-[13px]">
                <legend className="font-semibold text-gray-700 mb-2">
                  {item.texto}
                  {item.obrigatoria ? " *" : ""}
                </legend>
                {item.tipo === "TEXTO_LIVRE" ? (
                  <textarea
                    name={item.id}
                    rows={3}
                    required={item.obrigatoria}
                    className={field}
                  />
                ) : null}
                {item.tipo === "NOTA_5" || item.tipo === "NOTA_10" ? (
                  <select name={item.id} required={item.obrigatoria} className={field}>
                    <option value="">Escolha</option>
                    {Array.from(
                      { length: item.tipo === "NOTA_5" ? 5 : 10 },
                      (_, i) => i + 1,
                    ).map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                ) : null}
                {["SIM_NAO", "MULTIPLA_ESCOLHA", "CHECKBOX"].includes(item.tipo)
                  ? item.opcoes.map((op) => (
                      <label key={op.id} className="flex items-center gap-2 mb-1 text-gray-700">
                        <input
                          type={item.tipo === "CHECKBOX" ? "checkbox" : "radio"}
                          name={item.id}
                          value={op.id}
                          required={item.obrigatoria && item.tipo !== "CHECKBOX"}
                        />
                        {op.texto}
                      </label>
                    ))
                  : null}
              </fieldset>
            ))}
            <button
              type="submit"
              className="rounded-2xl py-3 text-white text-[14px] font-bold"
              style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
            >
              Enviar respostas
            </button>
          </form>
        ) : null}
        <Link to="/entrar" className="block text-center text-[12px] text-gray-500 mt-4">
          Ir para o login
        </Link>
      </div>
    </div>
  );
}
