import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Status, SeloOculto } from "./Card";
import { ANONIMATO_MINIMO } from "./regras";

export type NoOrg = { id: string; nome: string; chefe?: string; pessoas: number; nota?: number; filhos?: NoOrg[] };

/** Estrutura configurável por órgão. Equipes começam recolhidas. */
export function Organograma({ raiz }: { raiz: NoOrg }) {
  return (
    <div className="v7-org" role="tree" aria-label="Estrutura do órgão">
      <No no={raiz} nivel={0} />
    </div>
  );
}

function No({ no, nivel }: { no: NoOrg; nivel: number }) {
  const [aberto, setAberto] = useState(nivel < 2);
  const tem = !!no.filhos?.length;
  return (
    <div role="treeitem" aria-expanded={tem ? aberto : undefined} aria-level={nivel + 1}>
      <div className="v7-org-no">
        {tem ? (
          <button type="button" onClick={() => setAberto(!aberto)} aria-label={aberto ? `Recolher ${no.nome}` : `Expandir ${no.nome}`}>
            {aberto ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
        ) : (
          <span style={{ width: 20 }} />
        )}
        <div>
          <div className="nome">{no.nome}</div>
          {no.chefe ? <div style={{ fontSize: 12, color: "var(--hz-v7-muted)" }}>Chefia: {no.chefe}</div> : null}
        </div>
        <div className="meta">
          <span>{no.pessoas} pessoas</span>
          {no.nota === undefined ? null : no.pessoas < ANONIMATO_MINIMO ? <SeloOculto /> : <Status nota={no.nota} />}
        </div>
      </div>
      {tem && aberto ? (
        <div className="v7-org-filhos" role="group">
          {no.filhos!.map((f) => (
            <No key={f.id} no={f} nivel={nivel + 1} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
