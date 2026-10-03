import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search } from "lucide-react";

export type ProjetoInicio = {
  id: string;
  estado: string;
  rotulo: string;
  vinculo_titulo?: string | null;
  nome_fantasia?: string | null;
  razao_social?: string | null;
};

const ENCERRADOS = new Set(["ENCERRADO", "ARQUIVADO"]);

const ROTULO_ESTADO: Record<string, string> = {
  ABERTO: "Aberto",
  EM_ANDAMENTO: "Em andamento",
  ENCERRADO: "Encerrado",
  ARQUIVADO: "Arquivado",
};

function nomeTrabalho(projeto: ProjetoInicio) {
  return projeto.vinculo_titulo || projeto.nome_fantasia || projeto.razao_social || "Trabalho";
}

function nomeCliente(projeto: ProjetoInicio) {
  return projeto.nome_fantasia || projeto.razao_social || "Cliente";
}

function sigla(texto: string) {
  const partes = texto.trim().split(/\s+/).filter((parte) => parte.length > 2);
  const base = partes.length > 0 ? partes : texto.trim().split(/\s+/);
  return base
    .slice(0, 2)
    .map((parte) => parte[0])
    .join("")
    .toUpperCase();
}

function primeiroNome(nome: string) {
  return nome.trim().split(/\s+/)[0] || "Consultora";
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

type Filtro = "todos" | "andamento" | "encerrado";

export function InicioConsultoraNovo({
  nome,
  projetos,
  erro,
}: {
  nome: string;
  projetos: ProjetoInicio[];
  erro: string;
}) {
  const navigate = useNavigate();
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const abertos = projetos.filter((item) => item.estado === "ABERTO").length;
  const andamento = projetos.filter((item) => item.estado === "EM_ANDAMENTO").length;
  const encerrados = projetos.filter((item) => ENCERRADOS.has(item.estado)).length;

  const lista = useMemo(() => {
    const texto = busca.trim().toLowerCase();
    return projetos.filter((item) => {
      if (filtro === "andamento" && item.estado !== "EM_ANDAMENTO") return false;
      if (filtro === "encerrado" && !ENCERRADOS.has(item.estado)) return false;
      if (!texto) return true;
      return `${nomeTrabalho(item)} ${nomeCliente(item)} ${item.rotulo}`.toLowerCase().includes(texto);
    });
  }, [busca, filtro, projetos]);

  return (
    <div>
      <div className="min-[900px]:flex min-[900px]:items-start min-[900px]:justify-between min-[900px]:gap-6">
        <div>
          <p className="text-[13px] text-[var(--hz-muted-2)]">{dataCabecalho()}</p>
          <h1 className="mt-1 text-[32px] font-semibold tracking-tight">
            {saudacao()}, {primeiroNome(nome)}
          </h1>
        </div>
        <div className="mt-4 flex items-center gap-2 min-[900px]:mt-2 min-[900px]:w-[420px]">
          <label className="flex min-w-0 flex-1 items-center gap-2 rounded-full bg-white px-3 py-2.5 ring-1 ring-black/5">
            <Search size={16} className="text-[var(--hz-muted-2)]" aria-hidden="true" />
            <input
              value={busca}
              onChange={(evento) => setBusca(evento.target.value)}
              placeholder="Buscar órgão ou trabalho"
              className="min-w-0 flex-1 bg-transparent text-[14px] outline-none"
            />
          </label>
          <button
            type="button"
            onClick={() => navigate("/projetos/novo")}
            className="inline-flex shrink-0 items-center gap-1 rounded-xl bg-[var(--hz-ink)] px-4 py-2.5 text-[14px] font-semibold text-white"
          >
            <Plus size={16} />
            <span className="hidden min-[900px]:inline">Novo trabalho</span>
          </button>
        </div>
      </div>

      {erro ? <p className="mt-4 text-[13px] text-[var(--hz-danger)]">{erro}</p> : null}

      <section className="mt-5 grid grid-cols-2 gap-3 min-[900px]:grid-cols-3">
        <Cartao titulo="Abertos" valor={String(abertos)} detalhe="trabalhos" />
        <Cartao titulo="Em andamento" valor={String(andamento)} detalhe="agora" />
        <Cartao titulo="Encerrados" valor={String(encerrados)} detalhe={`de ${projetos.length}`} />
      </section>

      <section className="mt-4 rounded-[24px] bg-white p-4 ring-1 ring-black/[0.04]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-[18px] font-semibold">Trabalhos</h2>
            <p className="text-[13px] text-[var(--hz-muted)]">Os órgãos da sua conta</p>
          </div>
          <div className="flex rounded-full bg-[var(--hz-canvas-warm)] p-1 text-[12px]">
            {(
              [
                ["todos", "Todos"],
                ["andamento", "Em andamento"],
                ["encerrado", "Encerrados"],
              ] as const
            ).map(([chave, rotulo]) => (
              <button
                key={chave}
                type="button"
                aria-pressed={filtro === chave}
                onClick={() => setFiltro(chave)}
                className={`rounded-full px-3 py-1.5 ${
                  filtro === chave ? "bg-white font-semibold shadow-sm" : "text-[var(--hz-muted)]"
                }`}
              >
                {rotulo}
              </button>
            ))}
          </div>
        </div>
        <ul className="mt-3 divide-y divide-black/[0.05]">
          {lista.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => navigate(`/projetos/${item.id}`)}
                className="flex w-full items-center gap-3 py-3 text-left"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--hz-canvas-warm)] text-[11px] font-semibold">
                  {sigla(nomeCliente(item))}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{nomeTrabalho(item)}</span>
                  <span className="block truncate text-[12px] text-[var(--hz-muted-2)]">
                    {nomeCliente(item)} · {item.rotulo}
                  </span>
                </span>
                <span
                  className={`shrink-0 text-[12px] font-medium ${
                    item.estado === "EM_ANDAMENTO"
                      ? "text-[var(--hz-ok)]"
                      : ENCERRADOS.has(item.estado)
                        ? "text-[var(--hz-muted-2)]"
                        : "text-[var(--hz-warn)]"
                  }`}
                >
                  {ROTULO_ESTADO[item.estado] || item.estado}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {lista.length === 0 ? (
          <p className="py-6 text-[13px] text-[var(--hz-muted)]">
            {projetos.length === 0
              ? "Nenhum trabalho ainda. Crie o primeiro."
              : "Nenhum trabalho nesta busca."}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end border-t border-black/[0.05] pt-3">
          <button
            type="button"
            onClick={() => navigate("/consultora/pesquisas")}
            className="text-[13px] font-semibold"
          >
            Abrir pesquisas →
          </button>
        </div>
      </section>
    </div>
  );
}

function Cartao({ titulo, valor, detalhe }: { titulo: string; valor: string; detalhe: string }) {
  return (
    <article className="rounded-[22px] bg-white p-4 ring-1 ring-black/[0.04]">
      <p className="text-[13px] text-[var(--hz-muted)]">{titulo}</p>
      <p className="mt-2 text-[28px] font-semibold leading-none tracking-tight">
        {valor} <span className="text-[15px] font-medium">{detalhe}</span>
      </p>
    </article>
  );
}
