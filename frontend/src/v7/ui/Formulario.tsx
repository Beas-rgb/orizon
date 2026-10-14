import type { ReactNode } from "react";

export function Campo({ rotulo, valor, dica, tipo = "text", multilinha, erro }: { rotulo: string; valor?: string; dica?: string; tipo?: string; multilinha?: boolean; erro?: string }) {
  return (
    <label className="v7-campo-claro">
      <span>{rotulo}</span>
      {multilinha ? <textarea defaultValue={valor} rows={3} aria-invalid={!!erro} /> : <input type={tipo} defaultValue={valor} aria-invalid={!!erro} />}
      {erro ? <small className="erro" role="alert">{erro}</small> : dica ? <small>{dica}</small> : null}
    </label>
  );
}

export function Selecao({ rotulo, opcoes }: { rotulo: string; opcoes: string[] }) {
  return (
    <label className="v7-campo-claro">
      <span>{rotulo}</span>
      <select defaultValue={opcoes[0]}>{opcoes.map((o) => <option key={o}>{o}</option>)}</select>
    </label>
  );
}

export function Abas({ itens, ativa }: { itens: string[]; ativa: string }) {
  return (
    <div className="v7-abas" role="tablist">
      {itens.map((i) => (
        <button key={i} type="button" role="tab" aria-selected={i === ativa} className="v7-aba">{i}</button>
      ))}
    </div>
  );
}

export function Tabela({ colunas, linhas }: { colunas: string[]; linhas: ReactNode[][] }) {
  return (
    <div className="v7-rolagem">
      <table className="v7-tabela">
        <thead><tr>{colunas.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
        <tbody>{linhas.map((l, i) => <tr key={i}>{l.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export function Estado({ icone, titulo, texto, acoes, tom }: { icone: ReactNode; titulo: string; texto: ReactNode; acoes?: ReactNode; tom?: "ok" | "aviso" | "erro" | "neutro" }) {
  return (
    <div className="v7-card v7-estado" role={tom === "erro" ? "alert" : "status"}>
      <span className={`ic ${tom ?? "neutro"}`} aria-hidden="true">{icone}</span>
      <h2>{titulo}</h2>
      <div className="txt">{texto}</div>
      {acoes ? <div className="acoes">{acoes}</div> : null}
    </div>
  );
}
