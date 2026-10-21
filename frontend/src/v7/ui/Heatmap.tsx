import { ANONIMATO_MINIMO, faixa } from "./regras";

export type CelulaHeat = { nota: number; n: number };

/** Setor × dimensão. Abaixo de 5 respostas a célula vira "Oculto". */
export function Heatmap({ linhas, colunas, dados }: { linhas: string[]; colunas: string[]; dados: CelulaHeat[][] }) {
  return (
    <div className="v7-rolagem">
      <table className="v7-tabela v7-heat">
        <thead>
          <tr>
            <th scope="col">Setor</th>
            {colunas.map((c) => (
              <th key={c} scope="col" style={{ textAlign: "center" }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l, i) => (
            <tr key={l}>
              <th scope="row" style={{ background: "none", textTransform: "none", fontSize: 13, color: "var(--hz-v7-ink)", letterSpacing: 0 }}>
                {l}
              </th>
              {dados[i].map((c, j) =>
                c.n < ANONIMATO_MINIMO ? (
                  <td key={j} className="c oculto">
                    Oculto
                  </td>
                ) : (
                  <td key={j} className={`c ${faixa(c.nota)}`}>
                    {c.nota}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
