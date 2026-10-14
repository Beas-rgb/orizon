import { useRef, type ReactNode } from "react";
import { PanelLeftOpen, X } from "lucide-react";
import { LogoHorizon } from "../ui/LogoHorizon";
import { ListaItens, Rodape } from "./ItensMenu";
import type { ItemMenu } from "./menus";
import { useMenuAberto } from "./useMenuAberto";

type Props = { itens: ItemMenu[]; ativo: string; nome: string; papel: string; onSair?: () => void; children: ReactNode; abertoInicial?: boolean };

/**
 * DESKTOP (≥ 900 px). Menu fixo no canto (72 px, só ícones).
 * Hover (80 ms), foco (Tab) ou botão abrem o menu SUSPENSO (248 px) sobre o conteúdo — não empurra o layout —
 * com véu escurecido e desfocado (backdrop-filter). Esc ou clique no véu fecham.
 */
export function DesktopShell({ itens, ativo, nome, papel, onSair, children, abertoInicial }: Props) {
  const ref = useRef<HTMLElement>(null);
  const tempo = useRef<number | undefined>(undefined);
  const m = useMenuAberto();
  const aberto = m.aberto || !!abertoInicial;
  return (
    <div className="v7 v7-desktop">
      <div className="v7-veu" data-aberto={aberto} aria-hidden="true" onClick={m.fechar} />
      <aside
        id="v7-menu"
        ref={ref}
        className="v7-menu"
        data-aberto={aberto}
        aria-label="Menu principal"
        onMouseEnter={() => {
          window.clearTimeout(tempo.current);
          tempo.current = window.setTimeout(() => m.setHover(true), 80);
        }}
        onMouseLeave={() => {
          window.clearTimeout(tempo.current);
          m.setHover(false);
        }}
        onFocus={() => m.setFoco(true)}
        onBlur={(e) => {
          if (!ref.current?.contains(e.relatedTarget as Node)) m.setFoco(false);
        }}
      >
        <div className="topo">
          <LogoHorizon />
          <button type="button" className="v7-item v7-fixar" aria-label={m.preso ? "Fechar menu" : "Fixar menu aberto"} aria-pressed={m.preso} onClick={() => (m.preso ? m.fechar() : m.setPreso(true))}>
            {m.preso ? <X /> : <PanelLeftOpen />}
          </button>
        </div>
        <ListaItens itens={itens} ativo={ativo} mostrarTitulo={!aberto} aoEscolher={() => m.setPreso(false)} />
        <Rodape nome={nome} papel={papel} onSair={onSair} />
      </aside>
      <div className="v7-shell">
        <main className="v7-main" id="conteudo">
          {children}
        </main>
      </div>
    </div>
  );
}
