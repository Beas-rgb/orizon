import { Link } from "react-router-dom";
import { LogOut } from "lucide-react";
import type { ItemMenu } from "./menus";

export function ListaItens({ itens, ativo, mostrarTitulo, aoEscolher }: { itens: ItemMenu[]; ativo: string; mostrarTitulo: boolean; aoEscolher?: () => void }) {
  return (
    <nav aria-label="Principal">
      {itens.map((it, i) => {
        const g = it.grupo && it.grupo !== itens[i - 1]?.grupo ? it.grupo : "";
        return (
          <div key={it.id}>
            {g ? <div className="grupo">{g}</div> : null}
            <Link to={it.para} className="v7-item" aria-current={it.id === ativo ? "page" : undefined} title={mostrarTitulo ? it.rotulo : undefined} onClick={aoEscolher}>
              {it.icone}
              <span className="rotulo">{it.rotulo}</span>
              {it.cont ? <span className="cont rotulo">{it.cont}</span> : null}
            </Link>
          </div>
        );
      })}
    </nav>
  );
}

export function Rodape({ nome, papel, onSair }: { nome: string; papel: string; onSair?: () => void }) {
  const iniciais = nome.split(/\s+/).filter(Boolean).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="rodape">
      <div className="pessoa">
        <span className="v7-avatar" aria-hidden="true">{iniciais}</span>
        <span className="quem">
          <b>{nome}</b>
          <small>{papel}</small>
        </span>
      </div>
      <button type="button" className="v7-item" onClick={onSair}>
        <LogOut />
        <span className="rotulo">Sair</span>
      </button>
    </div>
  );
}
