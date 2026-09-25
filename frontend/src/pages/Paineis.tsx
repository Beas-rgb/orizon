import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
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
  const [params, setParams] = useSearchParams();
  const abaUrl = params.get("aba");
  const abaPesq =
    abaUrl === "agendadas" || abaUrl === "encerradas" || abaUrl === "historico"
      ? abaUrl
      : "ativas";

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

  const pesquisasFiltradas = pesquisas.filter((pe) => {
    if (abaPesq === "ativas") return pe.status === "PUBLICADA";
    if (abaPesq === "agendadas") return pe.status === "AGENDADA" || pe.status === "RASCUNHO";
    if (abaPesq === "encerradas") return pe.status === "ENCERRADA";
    return true; // historico = todas
  });

  const porAno = pesquisasFiltradas.reduce<Record<string, Pesquisa[]>>((acc, pe) => {
    // Sem data na listagem simples: agrupa por status no histórico.
    const chave = pe.status === "ENCERRADA" ? "Anteriores" : "Atuais";
    (acc[chave] ||= []).push(pe);
    return acc;
  }, {});

  return (
    <AppShell active="dashboard">
      <h1 className="text-[18px] font-bold text-gray-800 mb-1">Painel do órgão</h1>
      <p className="text-[12px] text-gray-500 mb-5">
        Só trabalhos em que você participa. Histórico de pesquisas antigas e novas.
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
          <h2 className="text-[14px] font-bold mb-3">Pesquisas</h2>
          {!ativo ? (
            <p className="text-gray-500 text-[13px]">Selecione um trabalho.</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {(
                  [
                    ["ativas", "Ativas"],
                    ["agendadas", "Agendadas"],
                    ["encerradas", "Encerradas"],
                    ["historico", "Histórico"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setParams({ aba: id })}
                    className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
                    style={{
                      background:
                        abaPesq === id
                          ? "rgba(29,95,175,0.15)"
                          : "rgba(255,255,255,0.5)",
                      color: abaPesq === id ? "#1D5FAF" : "#6b7280",
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {abaPesq === "historico" ? (
                Object.entries(porAno).map(([grupo, lista]) => (
                  <div key={grupo} className="mb-3">
                    <p className="text-[11px] font-bold text-gray-500 mb-1">{grupo}</p>
                    <ul className="flex flex-col gap-2">
                      {lista.map((pe) => (
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
                          {(pe.status === "PUBLICADA" || pe.status === "ENCERRADA") && (
                            <button
                              type="button"
                              onClick={() => void verResultado(pe.id)}
                              className="text-[12px] font-bold px-3 py-1.5 rounded-xl text-white"
                              style={{ background: ACCENT }}
                            >
                              Ver consolidado
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))
              ) : (
                <ul className="flex flex-col gap-2 mb-4">
                  {pesquisasFiltradas.map((pe) => (
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
                      {(pe.status === "PUBLICADA" || pe.status === "ENCERRADA") && (
                        <button
                          type="button"
                          onClick={() => void verResultado(pe.id)}
                          className="text-[12px] font-bold px-3 py-1.5 rounded-xl text-white"
                          style={{ background: ACCENT }}
                        >
                          Ver consolidado
                        </button>
                      )}
                    </li>
                  ))}
                  {pesquisasFiltradas.length === 0 ? (
                    <p className="text-gray-500 text-[13px]">Nenhuma nesta aba.</p>
                  ) : null}
                </ul>
              )}
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

type MinhaPesquisa = {
  pesquisa_id: string;
  projeto_id: string;
  titulo: string;
  tipo: string;
  status_participacao: string;
  disponivel_ate?: string | null;
  token?: string | null;
};

function rotuloStatus(status: string) {
  if (status === "EM_ANDAMENTO") return "Em andamento";
  if (status === "RESPONDIDA") return "Concluída";
  return "Pendente";
}

export function FuncionarioPainel() {
  const [itens, setItens] = useState<MinhaPesquisa[]>([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<MinhaPesquisa[]>("/eu/pesquisas")
      .then(setItens)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  const grupos: { chave: string; titulo: string; filtro: string[] }[] = [
    { chave: "pendentes", titulo: "Pendentes", filtro: ["PENDENTE"] },
    { chave: "andamento", titulo: "Em andamento", filtro: ["EM_ANDAMENTO"] },
    { chave: "concluidas", titulo: "Concluídas", filtro: ["RESPONDIDA"] },
  ];

  return (
    <AppShell active="dashboard">
      <h1 className="text-[18px] font-bold text-gray-800 mb-1">Minhas pesquisas</h1>
      <p className="text-[12px] text-gray-500 mb-5">
        Responda só com a sua conta de funcionário. O órgão vê o consolidado, não a sua resposta.
      </p>
      {erro ? <p className="text-[#A02828] text-[13px] mb-3">{erro}</p> : null}

      <div className="flex flex-col gap-5">
        {grupos.map((g) => {
          const lista = itens.filter((i) => g.filtro.includes(i.status_participacao));
          return (
            <div key={g.chave} className="rounded-3xl p-5" style={glassStyle}>
              <h2 className="text-[14px] font-bold mb-3">
                {g.titulo}{" "}
                <span className="text-gray-400 font-semibold">({lista.length})</span>
              </h2>
              <ul className="flex flex-col gap-2">
                {lista.map((p) => (
                  <li
                    key={p.pesquisa_id}
                    className="p-4 rounded-2xl flex flex-wrap items-center justify-between gap-3"
                    style={{
                      background: "rgba(255,255,255,0.55)",
                      border: "1px solid rgba(255,255,255,0.65)",
                    }}
                  >
                    <div>
                      <p className="text-[14px] font-semibold text-gray-800">{p.titulo}</p>
                      <p className="text-[12px] text-gray-500 mt-1">
                        {p.tipo} · {rotuloStatus(p.status_participacao)}
                        {p.disponivel_ate
                          ? ` · prazo ${new Date(p.disponivel_ate).toLocaleDateString("pt-BR")}`
                          : ""}
                      </p>
                    </div>
                    {p.status_participacao !== "RESPONDIDA" ? (
                      <Link
                        to={`/responder/pesquisa/${encodeURIComponent(p.pesquisa_id)}`}
                        className="rounded-xl py-2 px-4 text-white text-[12px] font-bold"
                        style={{ background: ACCENT }}
                      >
                        {p.status_participacao === "EM_ANDAMENTO" ? "Continuar" : "Responder"}
                      </Link>
                    ) : p.status_participacao === "RESPONDIDA" ? (
                      <span className="text-[12px] font-bold text-[#1E7A4A]">Respondida</span>
                    ) : null}
                  </li>
                ))}
                {lista.length === 0 ? (
                  <p className="text-gray-500 text-[13px]">Nenhuma neste grupo.</p>
                ) : null}
              </ul>
            </div>
          );
        })}
      </div>
    </AppShell>
  );
}

type Pedido = { id: string; nome: string; email: string; status: string };
type Consultora = { id: string; nome: string; email: string; ativo: boolean };
type DiagnosticoEmail = {
  provedor: string;
  remetente_configurado: boolean;
  remetente_eh_gmail?: boolean;
  conta_ti_recebe_email?: boolean;
  fallback_configurado: boolean;
  ultimas_20: number;
  aceitas: number;
  falhas: number;
  ultimo_status?: string | null;
  ultimo_provedor?: string | null;
  ultimo_erro?: string | null;
  avisos?: string[];
};

export function DevPainel() {
  const [saude, setSaude] = useState<{ status: string } | null>(null);
  const [banco, setBanco] = useState<{ status: string } | null>(null);
  const [email, setEmail] = useState<{ modo: string } | null>(null);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [consultores, setConsultores] = useState<Consultora[]>([]);
  const [diagnosticoEmail, setDiagnosticoEmail] = useState<DiagnosticoEmail | null>(
    null,
  );
  const [erro, setErro] = useState("");
  const [msg, setMsg] = useState("");
  const [linkAcesso, setLinkAcesso] = useState("");
  const [avisoEmail, setAvisoEmail] = useState("");
  const [testandoEmail, setTestandoEmail] = useState(false);
  const [destinoTeste, setDestinoTeste] = useState("");

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
    api<{ email_detalhe?: DiagnosticoEmail }>("/dev/diagnostico")
      .then((dados) => setDiagnosticoEmail(dados.email_detalhe || null))
      .catch(() => setDiagnosticoEmail(null));
  }, []);

  async function autorizar(id: string) {
    setMsg("");
    setErro("");
    setLinkAcesso("");
    setAvisoEmail("");
    try {
      const resp = await api<{
        mensagem: string;
        link_primeiro_acesso?: string | null;
        aviso_email?: string | null;
        email?: string;
      }>(`/dev/pedidos/${id}/autorizar`, {
        method: "POST",
      });
      setMsg(resp.mensagem || "Autorizado.");
      if (resp.aviso_email) setAvisoEmail(resp.aviso_email);
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
    setAvisoEmail("");
    try {
      const resp = await api<{
        mensagem: string;
        link_primeiro_acesso?: string | null;
        aviso_email?: string | null;
      }>(`/dev/consultores/${id}/reenviar-primeiro-acesso`, { method: "POST" });
      setMsg(resp.mensagem || "Reenviado.");
      if (resp.aviso_email) setAvisoEmail(resp.aviso_email);
      if (resp.link_primeiro_acesso) {
        setLinkAcesso(resp.link_primeiro_acesso);
      }
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  async function testarEnvioEmail() {
    setErro("");
    setMsg("");
    setAvisoEmail("");
    setTestandoEmail(true);
    try {
      const destino = destinoTeste.trim();
      const resposta = await api<{
        mensagem: string;
        status: string;
        provedor?: string | null;
        erro?: string | null;
        destino?: string | null;
      }>("/dev/diagnostico/email/teste", {
        method: "POST",
        json: destino ? { destino } : {},
      });
      setMsg(
        `${resposta.mensagem} Estado: ${resposta.status}${
          resposta.provedor ? ` via ${resposta.provedor}` : ""
        }${resposta.destino ? ` → ${resposta.destino}` : ""}.`,
      );
      if (resposta.erro) setAvisoEmail(resposta.erro);
      const diagnostico = await api<{ email_detalhe?: DiagnosticoEmail }>(
        "/dev/diagnostico",
      );
      setDiagnosticoEmail(diagnostico.email_detalhe || null);
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha ao testar e-mail");
    } finally {
      setTestandoEmail(false);
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
      {avisoEmail ? (
        <p className="text-[#A07020] text-[13px] mb-3">{avisoEmail}</p>
      ) : null}
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
            Senha nunca vem por e-mail. Abra o link ou copie o código após{" "}
            <code className="text-[11px]">?t=</code> em /primeiro-acesso.
          </p>
          <a className="text-[#1D5FAF] font-semibold underline" href={linkAcesso}>
            {linkAcesso}
          </a>
          <p className="mt-2 text-gray-500">
            Em desenvolvimento local:{" "}
            <code className="text-[11px]">
              http://127.0.0.1:8000/app/primeiro-acesso?t=
              {decodeURIComponent(
                (linkAcesso.split("t=")[1] || linkAcesso.split("#").pop() || "").split(
                  "&",
                )[0],
              )}
            </code>
          </p>
        </div>
      ) : null}

      {diagnosticoEmail ? (
        <div className="rounded-3xl p-4 mb-5 text-[12px]" style={glassStyle}>
          <p className="font-bold text-gray-800 mb-2">Diagnóstico de entrega</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-gray-600">
            <span>Provedor: {diagnosticoEmail.provedor}</span>
            <span>
              Remetente:{" "}
              {diagnosticoEmail.remetente_configurado ? "configurado" : "ausente"}
            </span>
            <span>Aceitas: {diagnosticoEmail.aceitas}</span>
            <span>Falhas: {diagnosticoEmail.falhas}</span>
          </div>
          {diagnosticoEmail.ultimo_status ? (
            <p className="mt-2 text-gray-600">
              Último envio: <strong>{diagnosticoEmail.ultimo_status}</strong>
              {diagnosticoEmail.ultimo_provedor
                ? ` via ${diagnosticoEmail.ultimo_provedor}`
                : ""}
            </p>
          ) : null}
          {diagnosticoEmail.ultimo_erro ? (
            <p className="mt-2 text-[#A02828]">{diagnosticoEmail.ultimo_erro}</p>
          ) : null}
          {diagnosticoEmail.ultimo_status === "ACEITO" ? (
            <p className="mt-2 text-[#A07020]">
              “Aceito” confirma a fila do provedor, não a chegada na caixa. Se não
              aparecer no Gmail, confira Suppressions/Activity e autenticação
              SPF/DKIM no SendGrid.
            </p>
          ) : null}
          {(diagnosticoEmail.avisos || []).map((aviso) => (
            <p key={aviso} className="mt-2 text-[#A07020]">
              {aviso}
            </p>
          ))}
          <label className="mt-3 block text-[11px] text-gray-500">
            Destino do teste (Gmail real — a conta TI .local não recebe)
            <input
              type="email"
              value={destinoTeste}
              onChange={(ev) => setDestinoTeste(ev.target.value)}
              placeholder="joao951biel@gmail.com"
              className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-[13px] text-gray-800"
            />
          </label>
          <button
            type="button"
            disabled={testandoEmail}
            onClick={() => void testarEnvioEmail()}
            className="mt-3 rounded-xl px-4 py-2 text-white font-bold disabled:opacity-60"
            style={{ background: ACCENT }}
          >
            {testandoEmail ? "Enviando teste…" : "Enviar teste de e-mail"}
          </button>
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
            No Render free o Gmail SMTP (porta 587) é bloqueado. Para demo real use{" "}
            <strong>SendGrid</strong> (API HTTPS) no serviço <code>orizon-api</code>:
          </p>
          <ol className="list-decimal pl-5 mb-2 space-y-1">
            <li>
              Crie conta em{" "}
              <a
                className="text-[#1D5FAF] underline"
                href="https://sendgrid.com"
                target="_blank"
                rel="noreferrer"
              >
                sendgrid.com
              </a>{" "}
              → Settings → Sender Authentication →{" "}
              <strong>Domain Authentication</strong> (SPF/DKIM). Single Sender
              com Gmail serve apenas para teste e pode cair no spam.
            </li>
            <li>
              Crie uma API Key (Mail Send) e no Render defina:
              <br />
              <code className="text-[11px] break-all">SENDGRID_API_KEY</code>
              <br />
              <code className="text-[11px] break-all">SENDGRID_FROM_EMAIL</code> = o
              Gmail verificado
              <br />
              <code className="text-[11px]">SENDGRID_FROM_NAME</code> = Horizon
            </li>
            <li>
              Opcional: configure também <code>MAILTRAP_API_TOKEN</code> e{" "}
              <code>MAILTRAP_FROM_EMAIL</code> como fallback.
            </li>
            <li>Salve e aguarde o redeploy.</li>
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
              → <code>{`{"modo":"sendgrid"}`}</code>.
            </li>
          </ol>
          <p className="text-gray-600">
            Enquanto estiver em <code>local</code>, use o link de primeiro acesso que
            aparece após autorizar. Senha nunca vai por e-mail.
          </p>
        </div>
      ) : email?.modo === "sendgrid" ? (
        <div
          className="rounded-3xl p-4 mb-5 text-[12px] text-[#1E7A4A]"
          style={{
            ...glassStyle,
            border: "1px solid rgba(30,122,74,0.3)",
            background: "rgba(30,122,74,0.08)",
          }}
        >
          Canal <strong>SendGrid</strong> ativo (HTTPS — ok no Render free). Convites
          saem do remetente verificado. Se não chegar, confira Inbox/Spam e o Activity
          do SendGrid.
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
          Canal de e-mail ativo (<strong>{email.modo}</strong>). No Render free, SMTP
          costuma falhar com &quot;Network is unreachable&quot; — prefira SendGrid. Mailtrap
          demo pode não entregar no Gmail real.
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
