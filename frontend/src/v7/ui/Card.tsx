import type { ReactNode } from "react";
import { EyeOff } from "lucide-react";

import { ANONIMATO_MINIMO, faixa, ROTULO_FAIXA } from "./regras";

export function Card({ titulo, sub, acao, children, className }: { titulo?: ReactNode; sub?: ReactNode; acao?: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <section className={["v7-card", className].filter(Boolean).join(" ")}>
      {titulo ? (
        <div className="v7-card-cab">
          <div>
            <h2>{titulo}</h2>
            {sub ? <p>{sub}</p> : null}
          </div>
          {acao}
        </div>
      ) : null}
      {children}
    </section>
  );
}

/** Cor só com texto: o selo sempre traz a palavra e, se houver, o número. */
export function Status({ nota, texto }: { nota?: number; texto?: string }) {
  if (nota === undefined) return <span className="v7-status neutro">{texto}</span>;
  const f = faixa(nota);
  return (
    <span className={`v7-status ${f}`}>
      {texto ?? ROTULO_FAIXA[f]} · {nota}
    </span>
  );
}

export function SeloOculto({ n }: { n?: number }) {
  return (
    <span className="v7-oculto" title={`Menos de ${ANONIMATO_MINIMO} respostas`}>
      <EyeOff size={12} aria-hidden="true" />
      Oculto{n !== undefined ? ` · ${n} resp.` : ""}
    </span>
  );
}

export function Kpi({ rotulo, valor, unidade, nota }: { rotulo: string; valor: ReactNode; unidade?: string; nota?: ReactNode }) {
  return (
    <div className="v7-card v7-kpi">
      <div className="rot">{rotulo}</div>
      <div className="val">
        {valor}
        {unidade ? <small>{unidade}</small> : null}
      </div>
      {nota ? <div className="nota">{nota}</div> : null}
    </div>
  );
}

export function LinhaNota({ nome, nota, n }: { nome: string; nota: number; n: number }) {
  if (n < ANONIMATO_MINIMO)
    return (
      <div className="v7-linha">
        <span>{nome}</span>
        <div className="v7-barra" />
        <SeloOculto n={n} />
      </div>
    );
  const f = faixa(nota);
  return (
    <div className="v7-linha">
      <span>{nome}</span>
      <div className="v7-barra" aria-hidden="true">
        <i className={f} style={{ width: `${nota}%` }} />
      </div>
      <Status nota={nota} />
    </div>
  );
}
