import type { ReactNode } from "react";
import { EstadoMensagem } from "./EstadoMensagem";

const caixa =
  "rounded-3xl p-6 text-center text-[13px] bg-[var(--hz-surface)] ring-1 ring-black/[0.05]";

export function TelaCarregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <div className={caixa} role="status">
      <EstadoMensagem tom="neutro">{texto}</EstadoMensagem>
    </div>
  );
}

export function TelaVazia({
  titulo = "Nada por aqui",
  texto = "Quando houver conteúdo, ele aparece nesta tela.",
}: {
  titulo?: string;
  texto?: string;
}) {
  return (
    <div className={caixa}>
      <p className="text-[15px] font-bold text-[var(--hz-ink)]">{titulo}</p>
      <EstadoMensagem tom="neutro">{texto}</EstadoMensagem>
    </div>
  );
}

export function TelaErro({
  texto = "Não foi possível carregar. Tente de novo.",
}: {
  texto?: string;
}) {
  return (
    <div className={caixa}>
      <EstadoMensagem tom="erro">{texto}</EstadoMensagem>
    </div>
  );
}

export function TelaSemPermissao() {
  return (
    <div className={caixa}>
      <p className="text-[15px] font-bold text-[var(--hz-ink)]">Sem permissão</p>
      <EstadoMensagem tom="aviso">
        Esta área não está no seu perfil. Se precisar, peça à consultora.
      </EstadoMensagem>
    </div>
  );
}

export function TelaEnviando({ texto = "Enviando…" }: { texto?: string }) {
  return (
    <div className={caixa} role="status">
      <EstadoMensagem tom="neutro">{texto}</EstadoMensagem>
    </div>
  );
}

export function TelaTempoEsgotado() {
  return (
    <div className={caixa}>
      <EstadoMensagem tom="aviso">O tempo esgotou. Tente de novo.</EstadoMensagem>
    </div>
  );
}

export function TelaSemConexao() {
  return (
    <div className={caixa}>
      <EstadoMensagem tom="erro">Sem conexão com o servidor.</EstadoMensagem>
    </div>
  );
}

export function Pagina404() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--hz-bg)] px-4">
      <div className={`${caixa} max-w-md`}>
        <p className="text-[15px] font-bold text-[var(--hz-ink)]">Página não encontrada</p>
        <EstadoMensagem tom="neutro">
          Confira o endereço ou volte ao início.
        </EstadoMensagem>
        <a href="/app/inicio" className="text-[13px] font-bold text-[var(--hz-accent)]">
          Ir ao início
        </a>
      </div>
    </div>
  );
}

export function Dialogo({
  titulo,
  children,
  onFechar,
}: {
  titulo: string;
  children: ReactNode;
  onFechar: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--hz-ink)]/40 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialogo-titulo"
    >
      <div className="w-full max-w-md rounded-3xl bg-[var(--hz-surface)] p-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 id="dialogo-titulo" className="text-[16px] font-bold text-[var(--hz-ink)]">
            {titulo}
          </h2>
          <button type="button" className="text-[13px]" onClick={onFechar}>
            Fechar
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
