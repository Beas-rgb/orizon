import type { ReactNode } from "react";
import "../../styles/v7.css";
import { DesktopShell } from "./DesktopShell";
import { MobileShell } from "./MobileShell";
import { menuDe, type Perfil } from "./menus";
import { useEhDesktop } from "./useBreakpoint";

type Props = { perfil: Perfil; ativo: string; nome: string; papel: string; children: ReactNode; orgaoVeOrganizacao?: boolean; menuAberto?: boolean; gavetaAberta?: boolean; onSair?: () => void; trabalhoId?: string };

/** menuAberto = menu suspenso aberto no desktop (tela 77); gavetaAberta = gaveta aberta no celular (tela 54).
 * Escolhe o layout pelo breakpoint: DesktopShell (≥ 900 px) ou MobileShell (< 900 px). O conteúdo é o mesmo. */
export function AppShellV7({ perfil, ativo, children, orgaoVeOrganizacao, menuAberto, gavetaAberta, trabalhoId, ...pessoa }: Props) {
  const desktop = useEhDesktop();
  const itens = menuDe(perfil, { orgaoVeOrganizacao, trabalhoId });
  const Shell = desktop ? DesktopShell : MobileShell;
  return (
    <Shell itens={itens} ativo={ativo} abertoInicial={desktop ? menuAberto : gavetaAberta} {...pessoa}>
      {children}
    </Shell>
  );
}

export function Cabecalho({ eyebrow, titulo, lede, migalha, acao }: { eyebrow?: string; titulo: string; lede?: string; migalha?: string[]; acao?: ReactNode }) {
  return (
    <header className="v7-cab">
      <div>
        {migalha ? (
          <nav className="v7-migalha" aria-label="Você está em">
            {migalha.slice(0, -1).map((m) => (
              <span key={m}>{m} ›</span>
            ))}
            <b>{migalha[migalha.length - 1]}</b>
          </nav>
        ) : null}
        {eyebrow ? <div className="v7-eyebrow">{eyebrow}</div> : null}
        <h1>{titulo}</h1>
        {lede ? <p className="v7-lede">{lede}</p> : null}
      </div>
      {acao ? <div className="v7-cab-acao">{acao}</div> : null}
    </header>
  );
}
