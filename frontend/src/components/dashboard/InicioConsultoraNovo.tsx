import { useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  BarChart2,
  Bell,
  Briefcase,
  ChevronRight,
  ClipboardList,
  Home,
  LayoutGrid,
  Lock,
  Plus,
  Search,
  Send,
  Settings,
  Users,
} from "lucide-react";

const CHAVE_DESIGN = "orizon-design-consultora";

type DesignTela = "atual" | "novo";
type FiltroTrabalho = "todos" | "andamento" | "encerrada";
type StatusAmostra = "andamento" | "agendada" | "encerrada";

type TrabalhoAmostra = {
  sigla: string;
  orgao: string;
  subtitulo: string;
  pesquisa: string;
  detalhe: string;
  status: StatusAmostra;
  percentual: number | null;
  respostasTexto: string;
  prazo: string;
  prazoSub: string;
};

const TRABALHOS: TrabalhoAmostra[] = [
  {
    sigla: "VA",
    orgao: "Prefeitura de Vale Azul",
    subtitulo: "Executivo municipal",
    pesquisa: "Pesquisa de Clima 2026",
    detalhe: "572 convidados",
    status: "andamento",
    percentual: 72,
    respostasTexto: "412 respostas",
    prazo: "02/10",
    prazoSub: "sexta",
  },
  {
    sigla: "RC",
    orgao: "Secretaria de Saúde de Rio Claro",
    subtitulo: "Saúde estadual",
    pesquisa: "Avaliação 360° · Gestores",
    detalhe: "142 avaliadores",
    status: "andamento",
    percentual: 38,
    respostasTexto: "54 respostas",
    prazo: "30/09",
    prazoSub: "em 2 dias",
  },
  {
    sigla: "SA",
    orgao: "Câmara Municipal de Serra Alta",
    subtitulo: "Legislativo municipal",
    pesquisa: "Avaliação de Desempenho",
    detalhe: "194 convidados",
    status: "andamento",
    percentual: 61,
    respostasTexto: "118 respostas",
    prazo: "09/10",
    prazoSub: "sexta",
  },
  {
    sigla: "CB",
    orgao: "Prefeitura de Campo Belo",
    subtitulo: "Rede municipal de ensino",
    pesquisa: "Avaliação 360° · Diretores",
    detalhe: "620 avaliadores",
    status: "andamento",
    percentual: 55,
    respostasTexto: "341 respostas",
    prazo: "14/10",
    prazoSub: "quarta",
  },
  {
    sigla: "MV",
    orgao: "Defensoria Pública de Monte Verde",
    subtitulo: "Justiça estadual",
    pesquisa: "Pesquisa de Clima 2026",
    detalhe: "310 convidados",
    status: "agendada",
    percentual: null,
    respostasTexto: "Abre em 05/10",
    prazo: "23/10",
    prazoSub: "sexta",
  },
  {
    sigla: "LS",
    orgao: "Previdência de Lagoa Serena",
    subtitulo: "Autarquia municipal",
    pesquisa: "Pesquisa de Clima 2026",
    detalhe: "88 convidados",
    status: "encerrada",
    percentual: 89,
    respostasTexto: "78 respostas",
    prazo: "18/09",
    prazoSub: "entregue",
  },
];

const ATENCAO = [
  {
    icone: "alerta" as const,
    titulo: "Adesão baixa em Rio Claro",
    detalhe: "38% de resposta · faltam 2 dias",
    noCelular: true,
  },
  {
    icone: "envio" as const,
    titulo: "76 convites na fila de envio",
    detalhe: "Serra Alta · saem amanhã, 8h",
    noCelular: true,
  },
  {
    icone: "pessoas" as const,
    titulo: "8 avaliados sem avaliadores",
    detalhe: "Campo Belo · 360° Diretores",
    noCelular: false,
  },
];

const PRAZOS = [
  { dia: "29", mes: "SET", titulo: "Envio de convites", detalhe: "Câmara de Serra Alta · amanhã" },
  { dia: "30", mes: "SET", titulo: "Encerramento da Avaliação 360°", detalhe: "Saúde de Rio Claro · quarta" },
  { dia: "02", mes: "OUT", titulo: "Encerramento do Clima 2026", detalhe: "Prefeitura de Vale Azul · sexta" },
];

const ROTULO_STATUS: Record<StatusAmostra, string> = {
  andamento: "Em andamento",
  agendada: "Agendada",
  encerrada: "Encerrada",
};

export function lerDesignConsultora(): DesignTela {
  try {
    return localStorage.getItem(CHAVE_DESIGN) === "novo" ? "novo" : "atual";
  } catch {
    return "atual";
  }
}

export function gravarDesignConsultora(valor: DesignTela) {
  localStorage.setItem(CHAVE_DESIGN, valor);
}

export function InterruptorDesign({
  valor,
  onChange,
}: {
  valor: DesignTela;
  onChange: (valor: DesignTela) => void;
}) {
  return (
    <div
      className="fixed z-[80] right-3 bottom-[5.25rem] min-[900px]:bottom-4 flex rounded-full bg-white p-1 shadow-lg ring-1 ring-black/10"
      role="group"
      aria-label="Design da tela"
    >
      {(["atual", "novo"] as const).map((opcao) => (
        <button
          key={opcao}
          type="button"
          aria-pressed={valor === opcao}
          onClick={() => onChange(opcao)}
          className={`rounded-full px-3 py-1.5 text-[12px] font-semibold capitalize ${
            valor === opcao ? "bg-[#171717] text-white" : "text-[#5c5c5c]"
          }`}
        >
          {opcao}
        </button>
      ))}
    </div>
  );
}

function primeiroNome(nome: string) {
  return nome.trim().split(/\s+/)[0] || "Consultora";
}

function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "OR";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

function saudacao(data = new Date()) {
  const hora = data.getHours();
  if (hora < 12) return "Bom dia";
  if (hora < 18) return "Boa tarde";
  return "Boa noite";
}

function dataCabecalho(data = new Date()) {
  const texto = data.toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function AnelRespostas() {
  const raio = 32;
  const volta = 2 * Math.PI * raio;
  const deslocamento = volta * (1 - 0.61);
  return (
    <div className="relative h-[92px] w-[92px] shrink-0">
      <svg viewBox="0 0 88 88" className="h-full w-full" aria-hidden="true">
        <circle cx="44" cy="44" r={raio} fill="none" stroke="#2e2e2e" strokeWidth="7" />
        <circle
          cx="44"
          cy="44"
          r={raio}
          fill="none"
          stroke="white"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={volta}
          strokeDashoffset={deslocamento}
          transform="rotate(-90 44 44)"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
        <span className="text-[18px] font-semibold leading-none">61%</span>
        <span className="mt-0.5 text-[9px] text-white/70">recebidas</span>
      </div>
    </div>
  );
}

function CartaoNumero({
  titulo,
  tituloLargo,
  valor,
  detalhe,
  selo,
  seloLargo,
  tom,
}: {
  titulo: string;
  tituloLargo?: string;
  valor: string;
  detalhe?: string;
  selo: string;
  seloLargo?: string;
  tom: "verde" | "cinza";
}) {
  return (
    <article className="rounded-[22px] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] ring-1 ring-black/[0.04]">
      <p className="text-[13px] text-[#6d6d6d]">
        <span className={tituloLargo ? "min-[900px]:hidden" : ""}>{titulo}</span>
        {tituloLargo ? <span className="hidden min-[900px]:inline">{tituloLargo}</span> : null}
      </p>
      <p className="mt-2 text-[28px] font-semibold leading-none tracking-tight">
        {valor}{" "}
        {detalhe ? <span className="text-[15px] font-medium text-[#1c1c1c]">{detalhe}</span> : null}
      </p>
      <span
        className={`mt-3 inline-flex max-w-full rounded-full px-2 py-1 text-[12px] font-medium leading-snug ${
          tom === "verde" ? "bg-[#e7f6ec] text-[#1c8a46]" : "bg-[#f2f2f0] text-[#5e5e5e]"
        }`}
      >
        <span className={seloLargo ? "min-[900px]:hidden" : ""}>{selo}</span>
        {seloLargo ? <span className="hidden min-[900px]:inline">{seloLargo}</span> : null}
      </span>
    </article>
  );
}

function CartaoRespostas() {
  return (
    <article className="rounded-[24px] bg-[#171717] p-4 text-white shadow-sm">
      <div className="flex items-center gap-4">
        <AnelRespostas />
        <div className="min-w-0">
          <p className="text-[13px] text-white/70">Respostas recebidas</p>
          <p className="mt-1 text-[26px] font-semibold leading-none tracking-tight">
            925 <span className="text-[16px] font-medium text-white/80">de 1.528</span>
          </p>
          <p className="mt-2 text-[13px] text-white/70">4 pesquisas em andamento</p>
        </div>
      </div>
      <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-[12px] text-white/85">
        <Lock size={12} aria-hidden="true" />
        Só dados agregados
      </p>
    </article>
  );
}

function IconeAtencao({ tipo }: { tipo: "alerta" | "envio" | "pessoas" }) {
  const classe = "flex h-9 w-9 items-center justify-center rounded-full bg-[#f4f1ea]";
  if (tipo === "alerta") {
    return (
      <span className={classe}>
        <AlertTriangle size={16} className="text-[#c47b12]" aria-hidden="true" />
      </span>
    );
  }
  if (tipo === "pessoas") {
    return (
      <span className={classe}>
        <Users size={16} className="text-[#5c5c5c]" aria-hidden="true" />
      </span>
    );
  }
  return (
    <span className={classe}>
      <Send size={16} className="text-[#5c5c5c]" aria-hidden="true" />
    </span>
  );
}

export function InicioConsultoraNovo({ nome }: { nome: string }) {
  const navigate = useNavigate();
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState<FiltroTrabalho>("todos");
  const [menuAberto, setMenuAberto] = useState(true);
  const curto = primeiroNome(nome);
  const sigla = iniciais(nome);
  const hoje = dataCabecalho();
  const ola = saudacao();

  const lista = useMemo(() => {
    const texto = busca.trim().toLowerCase();
    return TRABALHOS.filter((item) => {
      if (filtro !== "todos" && item.status !== filtro) return false;
      if (!texto) return true;
      return `${item.orgao} ${item.pesquisa}`.toLowerCase().includes(texto);
    });
  }, [busca, filtro]);

  const irTrabalhos = () => navigate("/projetos");
  const irPesquisas = () => navigate("/consultora/pesquisas");

  return (
    <div className="min-h-screen bg-[#f4f3ef] text-[#1c1c1c]">
      <div className="min-[900px]:flex">
        <aside
          className={`hidden min-[900px]:flex min-[900px]:flex-col min-[900px]:sticky min-[900px]:top-0 min-[900px]:h-screen min-[900px]:shrink-0 border-r border-black/[0.06] bg-[#f7f6f3] px-3 py-4 ${
            menuAberto ? "w-[248px]" : "w-[76px]"
          }`}
        >
          <div className="flex items-center gap-2 px-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#171717] text-[12px] font-semibold text-white">
              O
            </span>
            {menuAberto ? (
              <span>
                <span className="block text-[15px] font-semibold leading-none">Orizon</span>
                <span className="text-[10px] tracking-[0.14em] text-[#8a8a8a]">CONSULTORIA</span>
              </span>
            ) : null}
          </div>
          <p className="mt-6 px-3 text-[11px] font-medium tracking-wide text-[#8a8a8a]">
            {menuAberto ? "PRINCIPAL" : ""}
          </p>
          <nav className="mt-2 flex flex-col gap-1" aria-label="Principal">
            <ItemMenu rotulo="Início" icone={<Home size={16} />} ativo aberto={menuAberto} onClick={() => undefined} />
            <ItemMenu rotulo="Trabalhos" icone={<Briefcase size={16} />} selo="6" aberto={menuAberto} onClick={irTrabalhos} />
            <ItemMenu rotulo="Pesquisas" icone={<ClipboardList size={16} />} selo="9" aberto={menuAberto} onClick={irPesquisas} />
            <ItemMenu rotulo="Modelos" icone={<LayoutGrid size={16} />} aberto={menuAberto} />
            <ItemMenu rotulo="Resultados" icone={<BarChart2 size={16} />} aberto={menuAberto} />
          </nav>
          <p className="mt-6 px-3 text-[11px] font-medium tracking-wide text-[#8a8a8a]">
            {menuAberto ? "CONTA" : ""}
          </p>
          <nav className="mt-2" aria-label="Conta">
            <ItemMenu rotulo="Configurações" icone={<Settings size={16} />} aberto={menuAberto} />
          </nav>
          <div className="mt-auto flex items-center gap-2 px-2 pt-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#171717] text-[12px] font-semibold text-white">
              {sigla}
            </span>
            {menuAberto ? (
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-semibold">{nome}</span>
                <span className="text-[12px] text-[#6d6d6d]">Consultora</span>
              </span>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => setMenuAberto((aberto) => !aberto)}
            className="mt-3 px-3 py-2 text-left text-[12px] text-[#6d6d6d]"
          >
            {menuAberto ? "Recolher menu" : "Abrir"}
          </button>
        </aside>

        <div className="min-w-0 flex-1 pb-28 min-[900px]:pb-10">
          <header className="flex items-center justify-between px-4 pt-4 min-[900px]:hidden">
            <span className="flex items-center gap-2 font-semibold">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#171717] text-[12px] text-white">
                O
              </span>
              Orizon
            </span>
            <span className="flex items-center gap-2">
              <button type="button" aria-label="Avisos" className="flex h-9 w-9 items-center justify-center rounded-full bg-white ring-1 ring-black/5">
                <Bell size={16} />
              </button>
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#171717] text-[12px] font-semibold text-white">
                {sigla}
              </span>
            </span>
          </header>

          <div className="px-4 pt-5 min-[900px]:px-8 min-[900px]:pt-6">
            <div className="min-[900px]:flex min-[900px]:items-start min-[900px]:justify-between min-[900px]:gap-6">
              <div>
                <p className="text-[13px] text-[#8a8a8a]">{hoje}</p>
                <h1 className="mt-1 text-[32px] font-semibold tracking-tight min-[900px]:text-[36px]">
                  {ola}, {curto}
                </h1>
              </div>
              <div className="mt-4 flex items-center gap-2 min-[900px]:mt-2 min-[900px]:w-[460px]">
                <label className="flex min-w-0 flex-1 items-center gap-2 rounded-full bg-white px-3 py-2.5 ring-1 ring-black/5">
                  <Search size={16} className="text-[#8a8a8a]" aria-hidden="true" />
                  <input
                    value={busca}
                    onChange={(evento) => setBusca(evento.target.value)}
                    placeholder="Buscar órgão ou pesquisa"
                    className="min-w-0 flex-1 bg-transparent text-[14px] outline-none"
                  />
                  <kbd
                    aria-hidden="true"
                    className="hidden rounded-md bg-[#f3f3f1] px-1.5 py-0.5 text-[11px] text-[#6d6d6d] min-[900px]:inline"
                  >
                    ⌘K
                  </kbd>
                </label>
                <button
                  type="button"
                  aria-label="Nova pesquisa"
                  onClick={irPesquisas}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#171717] text-white min-[900px]:hidden"
                >
                  <Plus size={18} />
                </button>
                <button
                  type="button"
                  aria-label="Avisos"
                  className="hidden h-11 w-11 items-center justify-center rounded-full bg-white ring-1 ring-black/5 min-[900px]:flex"
                >
                  <Bell size={16} />
                </button>
                <button
                  type="button"
                  onClick={irPesquisas}
                  className="hidden shrink-0 items-center gap-1 rounded-full bg-[#171717] px-4 py-2.5 text-[14px] font-semibold text-white min-[900px]:inline-flex"
                >
                  <Plus size={16} />
                  Nova pesquisa
                </button>
              </div>
            </div>

            <section className="mt-5 grid grid-cols-2 gap-3 min-[900px]:grid-cols-4">
              <CartaoNumero
                titulo="Trabalhos ativos"
                valor="6"
                detalhe="órgãos"
                selo="↑ 1"
                seloLargo="↑ 1 novo contrato em setembro"
                tom="verde"
              />
              <CartaoNumero
                titulo="Em andamento"
                tituloLargo="Pesquisas em andamento"
                valor="4"
                detalhe="de 9"
                selo="1 agendada"
                seloLargo="1 agendada · começa em 05/10"
                tom="cinza"
              />
              <CartaoNumero
                titulo="Taxa média de resposta"
                valor="57%"
                selo="↑ 6 p.p."
                seloLargo="↑ 6 p.p. desde a semana passada"
                tom="verde"
              />
              <CartaoNumero
                titulo="Prazos nesta semana"
                valor="3"
                detalhe="entregas"
                selo="Próximo: amanhã, 29/09"
                tom="cinza"
              />
            </section>

            <div className="mt-4 min-[900px]:mt-5 min-[900px]:grid min-[900px]:grid-cols-[minmax(0,1fr)_320px] min-[900px]:items-start min-[900px]:gap-4">
              <section className="hidden rounded-[24px] bg-white p-4 ring-1 ring-black/[0.04] min-[900px]:block">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-[18px] font-semibold">Trabalhos</h2>
                    <p className="text-[13px] text-[#6d6d6d]">
                      Órgãos atendidos e a pesquisa em curso de cada um
                    </p>
                  </div>
                  <div className="flex rounded-full bg-[#f4f3ef] p-1 text-[12px]">
                    {(
                      [
                        ["todos", "Todos"],
                        ["andamento", "Em andamento"],
                        ["encerrada", "Encerrados"],
                      ] as const
                    ).map(([chave, rotulo]) => (
                      <button
                        key={chave}
                        type="button"
                        aria-pressed={filtro === chave}
                        onClick={() => setFiltro(chave)}
                        className={`rounded-full px-3 py-1.5 ${
                          filtro === chave ? "bg-white font-semibold shadow-sm" : "text-[#5c5c5c]"
                        }`}
                      >
                        {rotulo}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[680px] text-left text-[13px]">
                    <thead className="text-[11px] tracking-wide text-[#8a8a8a]">
                      <tr>
                        <th className="pb-2 font-medium">ÓRGÃO</th>
                        <th className="pb-2 font-medium">PESQUISA ATUAL</th>
                        <th className="pb-2 font-medium">STATUS</th>
                        <th className="pb-2 font-medium">RESPOSTAS</th>
                        <th className="pb-2 font-medium">PRAZO</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lista.map((item) => (
                        <tr key={item.sigla} className="border-t border-black/[0.05]">
                          <td className="py-3 pr-3">
                            <span className="flex items-center gap-2">
                              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f3f2ee] text-[11px] font-semibold">
                                {item.sigla}
                              </span>
                              <span>
                                <span className="block font-medium">{item.orgao}</span>
                                <span className="text-[12px] text-[#8a8a8a]">{item.subtitulo}</span>
                              </span>
                            </span>
                          </td>
                          <td className="py-3 pr-3">
                            <span className="block">{item.pesquisa}</span>
                            <span className="text-[12px] text-[#8a8a8a]">{item.detalhe}</span>
                          </td>
                          <td className="py-3 pr-3">
                            <span
                              className={
                                item.status === "andamento"
                                  ? "text-[#1f8a4c]"
                                  : item.status === "agendada"
                                    ? "text-[#c47b12]"
                                    : "text-[#8a8a8a]"
                              }
                            >
                              ● {ROTULO_STATUS[item.status]}
                            </span>
                          </td>
                          <td className="py-3 pr-3">
                            {item.percentual === null ? (
                              <span className="text-[#6d6d6d]">{item.respostasTexto}</span>
                            ) : (
                              <span>
                                <span className="font-medium">{item.percentual}%</span>
                                <span className="mt-1 block h-1 w-24 overflow-hidden rounded-full bg-[#eceae6]">
                                  <span
                                    className="block h-full bg-[#171717]"
                                    style={{ width: `${item.percentual}%` }}
                                  />
                                </span>
                                <span className="text-[12px] text-[#8a8a8a]">{item.respostasTexto}</span>
                              </span>
                            )}
                          </td>
                          <td className="py-3">
                            <span className="block font-medium">{item.prazo}</span>
                            <span className="text-[12px] text-[#8a8a8a]">{item.prazoSub}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {lista.length === 0 ? (
                    <p className="py-6 text-[13px] text-[#6d6d6d]">Nenhum trabalho da amostra nesta busca.</p>
                  ) : null}
                </div>
                <div className="mt-2 flex items-center justify-between gap-3 border-t border-black/[0.05] pt-3 text-[12px] text-[#6d6d6d]">
                  <span className="inline-flex items-center gap-1.5">
                    <Lock size={12} aria-hidden="true" />
                    Resultados exibidos apenas de forma agregada, sem respostas individuais
                  </span>
                  <button type="button" onClick={irTrabalhos} className="shrink-0 font-semibold text-[#1c1c1c]">
                    Ver todos os trabalhos →
                  </button>
                </div>
              </section>

              {busca.trim() ? (
                <ul className="mt-4 divide-y divide-black/[0.05] rounded-[22px] bg-white ring-1 ring-black/[0.04] min-[900px]:hidden">
                  {lista.map((item) => (
                    <li key={item.sigla} className="px-4 py-3 text-[14px]">
                      <span className="font-medium">{item.orgao}</span>
                      <span className="block text-[12px] text-[#6d6d6d]">{item.pesquisa}</span>
                    </li>
                  ))}
                  {lista.length === 0 ? (
                    <li className="px-4 py-4 text-[13px] text-[#6d6d6d]">Nenhum resultado nesta amostra.</li>
                  ) : null}
                </ul>
              ) : null}

              <div className="mt-4 flex flex-col gap-3 min-[900px]:mt-0">
                <div className="min-[900px]:order-none">
                  <CartaoRespostas />
                </div>
                <section className="rounded-[24px] bg-white p-4 ring-1 ring-black/[0.04]">
                  <div className="flex items-center justify-between">
                    <h2 className="text-[16px] font-semibold">Precisa da sua atenção</h2>
                    <button type="button" onClick={irTrabalhos} className="text-[13px] font-medium text-[#6d6d6d]">
                      Ver tudo
                    </button>
                  </div>
                  <ul className="mt-2">
                    {ATENCAO.filter((item) => item.noCelular).map((item) => (
                      <ItemAtencao key={item.titulo} item={item} />
                    ))}
                    {ATENCAO.filter((item) => !item.noCelular).map((item) => (
                      <li key={item.titulo} className="hidden min-[900px]:list-item">
                        <ItemAtencaoCorpo item={item} />
                      </li>
                    ))}
                  </ul>
                </section>
                <section className="hidden rounded-[24px] bg-white p-4 ring-1 ring-black/[0.04] min-[900px]:block">
                  <div className="flex items-center justify-between">
                    <h2 className="text-[16px] font-semibold">Próximos prazos</h2>
                    <span className="text-[13px] text-[#6d6d6d]">Agenda</span>
                  </div>
                  <ul className="mt-3 flex flex-col gap-3">
                    {PRAZOS.map((item) => (
                      <li key={item.titulo} className="flex items-center gap-3">
                        <span className="flex h-11 w-11 flex-col items-center justify-center rounded-2xl bg-[#171717] text-white">
                          <span className="text-[13px] font-semibold leading-none">{item.dia}</span>
                          <span className="text-[9px] tracking-wide">{item.mes}</span>
                        </span>
                        <span>
                          <span className="block text-[14px] font-medium">{item.titulo}</span>
                          <span className="text-[12px] text-[#6d6d6d]">{item.detalhe}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>
            </div>
          </div>
        </div>
      </div>

      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-black/[0.06] bg-[#f7f6f3] px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] min-[900px]:hidden"
        aria-label="Atalhos"
      >
        <Atalho rotulo="Início" icone={<Home size={18} />} ativo />
        <Atalho rotulo="Trabalhos" icone={<Briefcase size={18} />} onClick={irTrabalhos} />
        <Atalho rotulo="Pesquisas" icone={<ClipboardList size={18} />} onClick={irPesquisas} />
        <Atalho rotulo="Resultados" icone={<BarChart2 size={18} />} />
        <Atalho rotulo="Mais" icone={<LayoutGrid size={18} />} />
      </nav>
    </div>
  );
}

function ItemAtencao({
  item,
}: {
  item: (typeof ATENCAO)[number];
}) {
  return (
    <li>
      <ItemAtencaoCorpo item={item} />
    </li>
  );
}

function ItemAtencaoCorpo({ item }: { item: (typeof ATENCAO)[number] }) {
  return (
    <span className="flex items-center gap-3 py-2.5">
      <IconeAtencao tipo={item.icone} />
      <span className="min-w-0 flex-1">
        <span className="block text-[14px] font-medium">{item.titulo}</span>
        <span className="text-[12px] text-[#6d6d6d]">{item.detalhe}</span>
      </span>
      <ChevronRight size={16} className="text-[#b0b0b0]" aria-hidden="true" />
    </span>
  );
}

function ItemMenu({
  rotulo,
  icone,
  ativo = false,
  selo,
  aberto,
  onClick,
}: {
  rotulo: string;
  icone: ReactNode;
  ativo?: boolean;
  selo?: string;
  aberto: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={onClick ? rotulo : "Amostra do desenho. Esta tela ainda não abre."}
      className={`flex items-center gap-2 rounded-xl px-3 py-2 text-left text-[14px] ${
        ativo ? "bg-[#171717] font-medium text-white" : "text-[#3a3a3a]"
      }`}
    >
      {icone}
      {aberto ? <span className="flex-1">{rotulo}</span> : null}
      {aberto && selo ? (
        <span className={`rounded-full px-1.5 text-[11px] ${ativo ? "bg-white/15" : "bg-[#eceae6]"}`}>
          {selo}
        </span>
      ) : null}
    </button>
  );
}

function Atalho({
  rotulo,
  icone,
  ativo = false,
  onClick,
}: {
  rotulo: string;
  icone: ReactNode;
  ativo?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={onClick ? rotulo : "Amostra do desenho. Esta tela ainda não abre."}
      className={`flex min-w-0 flex-col items-center gap-1 px-1 text-[11px] ${
        ativo ? "font-semibold text-[#171717]" : "text-[#8a8a8a]"
      }`}
    >
      {icone}
      {rotulo}
    </button>
  );
}
