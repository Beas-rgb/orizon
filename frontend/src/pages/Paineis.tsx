import { useEffect, useState } from "react";
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

type Pesquisa = { id: string; titulo: string; tipo: string; status: string };
type PainelItem = {
  pergunta_id: string;
  texto: string;
  respostas: number;
  media?: number | null;
};

function nomeCliente(p: Projeto) {
  return p.nome_fantasia || p.razao_social || "Cliente";
}

export function OrgaoPainel() {
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [ativo, setAtivo] = useState<string | null>(null);
  const [pesquisas, setPesquisas] = useState<Pesquisa[]>([]);
  const [painel, setPainel] = useState<PainelItem[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Projeto[]>("/projetos")
      .then(setProjetos)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  async function abrir(id: string) {
    setAtivo(id);
    setPainel([]);
    setErro("");
    try {
      setPesquisas(await api<Pesquisa[]>(`/projetos/${id}/pesquisas`));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function verResultado(pesquisaId: string) {
    setErro("");
    try {
      setPainel(await api<PainelItem[]>(`/pesquisas/${pesquisaId}/painel`));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  return (
    <AppShell active="dashboard">
      <h1 className="text-[18px] font-bold text-gray-800 mb-1">Painel do órgão</h1>
      <p className="text-[12px] text-gray-500 mb-5">
        Só trabalhos em que você participa. Resultado agregado, sem nota individual.
      </p>
      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}

      <div className="grid lg:grid-cols-2 gap-5">
        <div className="rounded-3xl p-5" style={glassStyle}>
          <h2 className="text-[14px] font-bold mb-3">Meus trabalhos</h2>
          <ul className="flex flex-col gap-2">
            {projetos.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => void abrir(p.id)}
                  className="w-full text-left p-3 rounded-2xl"
                  style={{
                    background:
                      ativo === p.id ? "rgba(29,95,175,0.12)" : "rgba(255,255,255,0.55)",
                    border:
                      ativo === p.id
                        ? "1px solid rgba(29,95,175,0.22)"
                        : "1px solid rgba(255,255,255,0.65)",
                  }}
                >
                  <p className="text-[13px] font-semibold">
                    {p.vinculo_titulo || nomeCliente(p)}
                  </p>
                  <p className="text-[11px] text-gray-500">
                    {p.rotulo} · {p.estado}
                  </p>
                </button>
              </li>
            ))}
            {projetos.length === 0 ? (
              <p className="text-gray-500 text-[13px]">Nenhum trabalho no escopo.</p>
            ) : null}
          </ul>
        </div>

        <div className="rounded-3xl p-5" style={glassStyle}>
          <h2 className="text-[14px] font-bold mb-3">Resultado</h2>
          {!ativo ? (
            <p className="text-gray-500 text-[13px]">Selecione um trabalho.</p>
          ) : (
            <>
              <ul className="flex flex-col gap-2 mb-4">
                {pesquisas.map((pe) => (
                  <li
                    key={pe.id}
                    className="p-3 rounded-2xl flex flex-wrap items-center justify-between gap-2"
                    style={{ background: "rgba(255,255,255,0.55)" }}
                  >
                    <div>
                      <p className="text-[13px] font-semibold">{pe.titulo}</p>
                      <p className="text-[11px] text-gray-500">
                        {pe.tipo} · {pe.status}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void verResultado(pe.id)}
                      className="text-[12px] font-bold px-3 py-1.5 rounded-xl text-white"
                      style={{ background: ACCENT }}
                    >
                      Ver consolidado
                    </button>
                  </li>
                ))}
              </ul>
              {painel.map((item) => (
                <p key={item.pergunta_id} className="text-[12px] text-gray-600 mb-2">
                  {item.texto} · {item.respostas} respostas
                  {item.media != null ? ` · média ${item.media}` : ""}
                </p>
              ))}
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}

export function FuncionarioPainel() {
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [erro, setErro] = useState("");
  const [token, setToken] = useState("");

  useEffect(() => {
    api<Projeto[]>("/projetos")
      .then(setProjetos)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  return (
    <AppShell active="dashboard">
      <h1 className="text-[18px] font-bold text-gray-800 mb-1">Início do funcionário</h1>
      <p className="text-[12px] text-gray-500 mb-5">
        Seus trabalhos. Responda pelo link da pesquisa (token) e veja a própria nota quando houver.
      </p>
      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}
      <div className="rounded-3xl p-5 mb-4" style={glassStyle}>
        <p className="text-[13px] font-bold text-gray-800 mb-2">Abrir pesquisa pelo token</p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Cole o token do link"
            className="flex-1 rounded-xl px-3 py-2.5 text-[13px] outline-none bg-white/70 border border-white/80"
          />
          <a
            href={token.trim() ? `/app/responder/${encodeURIComponent(token.trim())}` : "#"}
            className="rounded-xl py-2.5 px-4 text-center text-white text-[13px] font-bold"
            style={{ background: ACCENT, opacity: token.trim() ? 1 : 0.5 }}
            onClick={(e) => {
              if (!token.trim()) e.preventDefault();
            }}
          >
            Responder
          </a>
        </div>
      </div>
      <div className="rounded-3xl p-5" style={glassStyle}>
        <ul className="flex flex-col gap-2">
          {projetos.map((p) => (
            <li
              key={p.id}
              className="p-4 rounded-2xl"
              style={{
                background: "rgba(255,255,255,0.55)",
                border: "1px solid rgba(255,255,255,0.65)",
              }}
            >
              <p className="text-[14px] font-semibold text-gray-800">
                {p.vinculo_titulo || nomeCliente(p)}
              </p>
              <p className="text-[12px] text-gray-500 mt-1">
                {nomeCliente(p)} · {p.rotulo} · {p.estado}
              </p>
            </li>
          ))}
          {projetos.length === 0 ? (
            <p className="text-gray-500 text-[13px]">Nenhum trabalho atribuído.</p>
          ) : null}
        </ul>
      </div>
    </AppShell>
  );
}

type Pedido = { id: string; nome: string; email: string; status: string };
type Consultora = { id: string; nome: string; email: string; ativo: boolean };

export function DevPainel() {
  const [saude, setSaude] = useState<{ status: string } | null>(null);
  const [banco, setBanco] = useState<{ status: string } | null>(null);
  const [email, setEmail] = useState<{ modo: string } | null>(null);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [consultores, setConsultores] = useState<Consultora[]>([]);
  const [erro, setErro] = useState("");
  const [msg, setMsg] = useState("");
  const [linkAcesso, setLinkAcesso] = useState("");

  useEffect(() => {
    api<{ status: string }>("/health").then(setSaude).catch(() => setSaude({ status: "falha" }));
    api<{ status: string }>("/health/db")
      .then(setBanco)
      .catch((exc) => setBanco({ status: exc instanceof Error ? exc.message : "falha" }));
    api<{ modo: string }>("/health/email")
      .then(setEmail)
      .catch((exc) => setEmail({ modo: exc instanceof Error ? exc.message : "falha" }));
    api<Pedido[]>("/dev/pedidos")
      .then(setPedidos)
      .catch(() => setPedidos([]));
    api<Consultora[]>("/dev/consultores")
      .then(setConsultores)
      .catch(() => setConsultores([]));
  }, []);

  async function autorizar(id: string) {
    setMsg("");
    setErro("");
    setLinkAcesso("");
    try {
      const resp = await api<{
        mensagem: string;
        link_primeiro_acesso?: string | null;
        email?: string;
      }>(`/dev/pedidos/${id}/autorizar`, {
        method: "POST",
      });
      setMsg(resp.mensagem || "Autorizado.");
      if (resp.link_primeiro_acesso) {
        setLinkAcesso(resp.link_primeiro_acesso);
      }
      setPedidos(await api<Pedido[]>("/dev/pedidos"));
      setConsultores(await api<Consultora[]>("/dev/consultores"));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function reenviarAcesso(id: string) {
    setMsg("");
    setErro("");
    setLinkAcesso("");
    try {
      const resp = await api<{
        mensagem: string;
        link_primeiro_acesso?: string | null;
      }>(`/dev/consultores/${id}/reenviar-primeiro-acesso`, { method: "POST" });
      setMsg(resp.mensagem || "Reenviado.");
      if (resp.link_primeiro_acesso) {
        setLinkAcesso(resp.link_primeiro_acesso);
      }
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  return (
    <AppShell active="dashboard">
      <h1 className="text-[18px] font-bold text-gray-800 mb-1">Desenvolvimento</h1>
      <p className="text-[12px] text-gray-500 mb-5">
        Diagnóstico e autorização de consultoras. Sem acesso a dados de negócio.
      </p>
      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}
      {msg ? <p className="text-[#1E7A4A] text-[13px] mb-3">{msg}</p> : null}
      {linkAcesso ? (
        <div
          className="rounded-2xl p-4 mb-5 text-[12px] break-all"
          style={{
            background: "rgba(29,95,175,0.08)",
            border: "1px solid rgba(29,95,175,0.2)",
          }}
        >
          <p className="font-bold text-gray-800 mb-1">Link de primeiro acesso (só para o TI)</p>
          <p className="text-gray-600 mb-2">
            Senha nunca vem por e-mail. Abra o link ou use a parte depois do # em
            /primeiro-acesso.
          </p>
          <a className="text-[#1D5FAF] font-semibold underline" href={linkAcesso}>
            {linkAcesso}
          </a>
          <p className="mt-2 text-gray-500">
            Em desenvolvimento local:{" "}
            <code className="text-[11px]">
              http://127.0.0.1:8000/app/primeiro-acesso#
              {decodeURIComponent(linkAcesso.split("#").pop() || "")}
            </code>
          </p>
        </div>
      ) : null}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-5">
        {[
          ["API", saude?.status || "…"],
          ["Banco", banco?.status || "…"],
          ["E-mail", email?.modo || "…"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-3xl p-4" style={glassStyle}>
            <p className="text-[11px] text-gray-500">{k}</p>
            <p className="text-[16px] font-bold text-gray-800 mt-1">{v}</p>
          </div>
        ))}
      </div>

      {email?.modo === "local" ? (
        <div
          className="rounded-3xl p-4 sm:p-5 mb-5 text-[12px] text-gray-700 leading-relaxed"
          style={{
            ...glassStyle,
            border: "1px solid rgba(160,112,32,0.35)",
            background: "rgba(160,112,32,0.08)",
          }}
        >
          <p className="font-bold text-gray-800 mb-2">E-mail ainda em modo local</p>
          <p className="mb-2">
            Convites não chegam na caixa real. Para testar envio/recebimento de verdade,
            preencha no painel do <strong>Render</strong> (Environment):
          </p>
          <ol className="list-decimal pl-5 mb-2 space-y-1">
            <li>
              Em <a className="text-[#1D5FAF] underline" href="https://mailtrap.io" target="_blank" rel="noreferrer">mailtrap.io</a>{" "}
              crie um token de API (Email Sending).
            </li>
            <li>
              No Render → serviço <code>orizon-api</code> → Environment, defina:
              <br />
              <code className="text-[11px] break-all">MAILTRAP_API_TOKEN</code> = o token
              <br />
              <code className="text-[11px] break-all">MAILTRAP_FROM_EMAIL</code> = remetente
              liberado no Mailtrap
              <br />
              <code className="text-[11px]">MAILTRAP_FROM_NAME</code> = Horizon
              <br />
              <code className="text-[11px] break-all">APP_PUBLIC_URL</code> =
              https://orizon-api.onrender.com/app
            </li>
            <li>Salve e aguarde o redeploy (ou Manual Deploy).</li>
            <li>
              Confira{" "}
              <a
                className="text-[#1D5FAF] underline break-all"
                href="https://orizon-api.onrender.com/health/email"
                target="_blank"
                rel="noreferrer"
              >
                /health/email
              </a>{" "}
              → deve mostrar <code>{`{"modo":"mailtrap"}`}</code>.
            </li>
          </ol>
          <p className="text-gray-600">
            Enquanto estiver em <code>local</code>, use o link de primeiro acesso que aparece
            após autorizar (acima). Senha nunca vai por e-mail.
          </p>
        </div>
      ) : email?.modo === "mailtrap" || email?.modo === "smtp" ? (
        <div
          className="rounded-3xl p-4 mb-5 text-[12px] text-[#1E7A4A]"
          style={{
            ...glassStyle,
            border: "1px solid rgba(30,122,74,0.3)",
            background: "rgba(30,122,74,0.08)",
          }}
        >
          Canal de e-mail ativo (<strong>{email.modo}</strong>). Convites devem chegar ao
          destinatário. Se não chegar, confira o Inbox/Spam do Mailtrap e o remetente
          autorizado.
        </div>
      ) : null}

      <div className="rounded-3xl p-5" style={glassStyle}>
        <h2 className="text-[14px] font-bold mb-3">Pedidos de consultora</h2>
        <ul className="flex flex-col gap-2">
          {pedidos.map((p) => (
            <li
              key={p.id}
              className="p-3 rounded-2xl flex flex-wrap items-center justify-between gap-2"
              style={{ background: "rgba(255,255,255,0.55)" }}
            >
              <div>
                <p className="text-[13px] font-semibold">{p.nome}</p>
                <p className="text-[11px] text-gray-500">
                  {p.email} · {p.status}
                </p>
              </div>
              {p.status === "PENDENTE" ? (
                <button
                  type="button"
                  onClick={() => void autorizar(p.id)}
                  className="px-3 py-1.5 rounded-xl text-white text-[12px] font-bold"
                  style={{ background: ACCENT }}
                >
                  Autorizar
                </button>
              ) : null}
            </li>
          ))}
          {pedidos.length === 0 ? (
            <p className="text-gray-500 text-[13px]">Nenhum pedido.</p>
          ) : null}
        </ul>
      </div>

      <div className="rounded-3xl p-5 mt-5" style={glassStyle}>
        <h2 className="text-[14px] font-bold mb-2">Consultoras</h2>
        <p className="text-[12px] text-gray-500 mb-3">
          Se autorizou e não chegou e-mail: use <strong>Reenviar primeiro acesso</strong>.
          O link aparece acima (em development). Senha você cria na tela de primeiro
          acesso — ela nunca vem no e-mail.
        </p>
        <ul className="flex flex-col gap-2">
          {consultores.map((c) => (
            <li
              key={c.id}
              className="p-3 rounded-2xl flex flex-wrap items-center justify-between gap-2"
              style={{ background: "rgba(255,255,255,0.55)" }}
            >
              <div>
                <p className="text-[13px] font-semibold">{c.nome}</p>
                <p className="text-[11px] text-gray-500">
                  {c.email} · {c.ativo ? "ativa" : "aguardando senha"}
                </p>
              </div>
              {!c.ativo ? (
                <button
                  type="button"
                  onClick={() => void reenviarAcesso(c.id)}
                  className="px-3 py-1.5 rounded-xl text-white text-[12px] font-bold"
                  style={{ background: ACCENT }}
                >
                  Reenviar primeiro acesso
                </button>
              ) : null}
            </li>
          ))}
          {consultores.length === 0 ? (
            <p className="text-gray-500 text-[13px]">Nenhuma consultora ainda.</p>
          ) : null}
        </ul>
      </div>
    </AppShell>
  );
}
