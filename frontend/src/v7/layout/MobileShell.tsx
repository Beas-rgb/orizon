import { useCallback, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Bell, Menu as IconeMenu, X } from "lucide-react";
import { LogoHorizon } from "../ui/LogoHorizon";
import { ListaItens, Rodape } from "./ItensMenu";
import type { ItemMenu } from "./menus";
import { useMenuAberto } from "./useMenuAberto";

type Props = { itens: ItemMenu[]; ativo: string; nome: string; papel: string; onSair?: () => void; children: ReactNode; abertoInicial?: boolean };

/**
 * CELULAR (< 900 px). Topo com logo + sino + ☰; barra inferior com 3 atalhos + "Menu".
 * ☰/Menu abrem a GAVETA pela esquerda, com o mesmo véu desfocado. Esc/véu/✕ fecham e devolvem o foco ao ☰.
 */
export function MobileShell({ itens, ativo, nome, papel, onSair, children, abertoInicial }: Props) {
  const botao = useRef<HTMLButtonElement>(null);
  const devolver = useCallback(() => botao.current?.focus(), []);
  const m = useMenuAberto(devolver);
  const aberto = m.preso || !!abertoInicial;
  const baixo = itens.filter((i) => i.baixo).slice(0, 3);
  return (
    <div className="v7 v7-mobile">
      <header className="v7-topo-cel">
        <LogoHorizon altura={24} />
        <div style={{ display: "flex", gap: 4 }}>
          <Link to="/notificacoes" className="v7-btn fantasma" aria-label="Notificações"><Bell /></Link>
          <button ref={botao} type="button" className="v7-btn fantasma" aria-label="Abrir menu" aria-expanded={aberto} aria-controls="v7-gaveta" onClick={() => m.setPreso(true)}>
            <IconeMenu />
          </button>
        </div>
      </header>
      <main className="v7-main" id="conteudo">
        {children}
      </main>
      <nav className="v7-baixo" aria-label="Atalhos">
        {baixo.map((i) => (
          <Link key={i.id} to={i.para} className="v7-item" aria-current={i.id === ativo ? "page" : undefined}>
            {i.icone}
            {i.rotulo.split(" ")[0]}
          </Link>
        ))}
        <button type="button" className="v7-item" aria-controls="v7-gaveta" aria-expanded={aberto} onClick={() => m.setPreso(true)}>
          <IconeMenu />
          Menu
        </button>
      </nav>
      <div className="v7-veu" data-aberto={aberto} aria-hidden="true" onClick={m.fechar} />
      <aside id="v7-gaveta" className="v7-menu v7-gaveta" data-aberto={aberto} aria-label="Menu principal" aria-hidden={!aberto} inert={!aberto}>
        <div className="topo">
          <LogoHorizon />
          <button type="button" className="v7-item v7-fixar" aria-label="Fechar menu" onClick={() => { m.fechar(); devolver(); }}>
            <X />
          </button>
        </div>
        <ListaItens itens={itens} ativo={ativo} mostrarTitulo={false} aoEscolher={m.fechar} />
        <Rodape nome={nome} papel={papel} onSair={onSair} />
      </aside>
    </div>
  );
}
