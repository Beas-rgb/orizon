import { useMemo, useState } from "react";
import { ACCENT } from "../../lib/theme";
import type { NoArvore } from "./tipos";

function combina(no: NoArvore, busca: string) {
  const q = busca.trim().toLowerCase();
  if (!q) return true;
  return (
    no.nome.toLowerCase().includes(q) ||
    no.email.toLowerCase().includes(q) ||
    (no.cargo || "").toLowerCase().includes(q) ||
    (no.setor || "").toLowerCase().includes(q)
  );
}

function filtrarArvore(nos: NoArvore[], busca: string): NoArvore[] {
  if (!busca.trim()) return nos;
  return nos.flatMap((no) => {
    const filhos = filtrarArvore(no.subordinados, busca);
    if (combina(no, busca)) {
      return [{ ...no, subordinados: no.subordinados }];
    }
    if (filhos.length > 0) {
      return [{ ...no, subordinados: filhos }];
    }
    return [];
  });
}

function idsVisiveis(nos: NoArvore[]): string[] {
  return nos.flatMap((no) => [no.usuario_id, ...idsVisiveis(no.subordinados)]);
}

function contar(nos: NoArvore[]): number {
  return nos.reduce((acc, no) => acc + 1 + contar(no.subordinados), 0);
}

function destacar(texto: string, busca: string) {
  const q = busca.trim();
  if (!q) return texto;
  const idx = texto.toLowerCase().indexOf(q.toLowerCase());
  if (idx < 0) return texto;
  return (
    <>
      {texto.slice(0, idx)}
      <mark className="bg-yellow-100 text-gray-800 rounded px-0.5">
        {texto.slice(idx, idx + q.length)}
      </mark>
      {texto.slice(idx + q.length)}
    </>
  );
}

function NoItem({
  no,
  nivel,
  aberta,
  busca,
  onAlternar,
}: {
  no: NoArvore;
  nivel: number;
  aberta: Set<string>;
  busca: string;
  onAlternar: (id: string) => void;
}) {
  const temFilhos = no.subordinados.length > 0;
  const expandido = aberta.has(no.usuario_id);
  const cargoSetor = [no.cargo, no.setor].filter(Boolean).join(" · ");
  return (
    <div style={{ marginLeft: nivel * 18 }}>
      <div
        className="flex items-center gap-2 rounded-xl px-3 py-2"
        style={{ background: "rgba(255,255,255,0.55)" }}
      >
        {temFilhos ? (
          <button
            type="button"
            onClick={() => onAlternar(no.usuario_id)}
            className="text-[12px] font-bold w-5 shrink-0"
            style={{ color: ACCENT }}
            aria-label={expandido ? "Recolher" : "Expandir"}
          >
            {expandido ? "−" : "+"}
          </button>
        ) : (
          <span className="w-5 shrink-0" />
        )}
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-gray-800 truncate">
            {destacar(no.nome, busca)}
          </p>
          <p className="text-[11px] text-gray-500 truncate">
            {destacar(no.email, busca)}
            {cargoSetor ? ` · ${cargoSetor}` : ""}
          </p>
        </div>
        {temFilhos ? (
          <span className="ml-auto text-[10px] font-bold text-gray-400 shrink-0">
            {no.subordinados.length}
          </span>
        ) : null}
      </div>
      {expandido
        ? no.subordinados.map((filho) => (
            <NoItem
              key={filho.usuario_id}
              no={filho}
              nivel={nivel + 1}
              aberta={aberta}
              busca={busca}
              onAlternar={onAlternar}
            />
          ))
        : null}
    </div>
  );
}

export function ArvoreOrganizacional({
  arvore,
  vazio = "Nenhum funcionário com perfil ainda. Importe ou defina o superior.",
}: {
  arvore: NoArvore[];
  vazio?: string;
}) {
  const [busca, setBusca] = useState("");
  const [manual, setManual] = useState<Set<string> | null>(null);

  const visivel = useMemo(() => filtrarArvore(arvore, busca), [arvore, busca]);
  const total = contar(arvore);
  const padrao = useMemo(() => {
    if (busca.trim()) return new Set(idsVisiveis(visivel));
    return new Set(arvore.map((no) => no.usuario_id));
  }, [busca, visivel, arvore]);
  const aberta = manual ?? padrao;

  function alternar(id: string) {
    setManual(() => {
      const novo = new Set(aberta);
      if (novo.has(id)) novo.delete(id);
      else novo.add(id);
      return novo;
    });
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <input
          type="search"
          placeholder="Buscar por nome, e-mail, cargo ou setor"
          className="flex-1 min-w-[12rem] rounded-xl px-3 py-2 text-[13px] outline-none bg-white/70 border border-white/80"
          value={busca}
          onChange={(e) => {
            setBusca(e.target.value);
            setManual(null);
          }}
        />
        <button
          type="button"
          className="text-[12px] font-bold px-3 py-2 rounded-xl"
          style={{ background: "rgba(29,95,175,0.10)", color: ACCENT }}
          onClick={() => setManual(new Set(idsVisiveis(visivel)))}
        >
          Expandir tudo
        </button>
        <button
          type="button"
          className="text-[12px] font-bold px-3 py-2 rounded-xl text-gray-600"
          style={{ background: "rgba(0,0,0,0.05)" }}
          onClick={() => setManual(new Set())}
        >
          Recolher
        </button>
      </div>
      <p className="text-[11px] text-gray-500 mb-2">
        {total} {total === 1 ? "pessoa" : "pessoas"}
        {busca.trim() ? ` · ${contar(visivel)} na busca` : ""}
        . A árvore vem do superior, não do setor.
      </p>
      <div className="flex flex-col gap-1">
        {visivel.map((no) => (
          <NoItem
            key={no.usuario_id}
            no={no}
            nivel={0}
            aberta={aberta}
            busca={busca}
            onAlternar={alternar}
          />
        ))}
        {arvore.length === 0 ? (
          <p className="text-gray-500 text-[13px]">{vazio}</p>
        ) : visivel.length === 0 ? (
          <p className="text-gray-500 text-[13px]">Nada corresponde à busca.</p>
        ) : null}
      </div>
    </div>
  );
}
