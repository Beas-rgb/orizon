import { useId } from "react";

type Variante = "simbolo" | "horizontal" | "empilhado";
type Tom = "claro" | "escuro";

type Props = {
  variante?: Variante;
  tamanho?: number;
  tom?: Tom;
};

function Simbolo({ tamanho, prefixo }: { tamanho: number; prefixo: string }) {
  const jet = `${prefixo}-jet`;
  const halo = `${prefixo}-halo`;
  return (
    <svg
      width={tamanho * 2.6}
      height={tamanho}
      viewBox="0 0 260 100"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={jet} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--hz-mark-glow)" stopOpacity="0" />
          <stop offset="50%" stopColor="var(--hz-mark-core)" stopOpacity="1" />
          <stop offset="100%" stopColor="var(--hz-mark-glow)" stopOpacity="0" />
        </linearGradient>
        <radialGradient id={halo} cx="50%" cy="50%" r="50%">
          <stop offset="42%" stopColor="var(--hz-mark-void)" />
          <stop offset="58%" stopColor="var(--hz-mark-core)" />
          <stop offset="72%" stopColor="var(--hz-mark-glow)" stopOpacity="0.85" />
          <stop offset="100%" stopColor="var(--hz-mark-glow)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <polygon points="0,50 108,40 108,60" fill={`url(#${jet})`} />
      <polygon points="260,50 152,36 152,64" fill={`url(#${jet})`} />
      <circle cx="130" cy="50" r="36" fill={`url(#${halo})`} />
      <circle cx="130" cy="50" r="22" fill="var(--hz-mark-void)" />
    </svg>
  );
}

export function Logo({
  variante = "simbolo",
  tamanho = 48,
  tom = "claro",
}: Props) {
  const prefixo = useId().replace(/:/g, "");
  const cor = tom === "escuro" ? "var(--hz-auth-text)" : "var(--hz-text)";
  const nome = (
    <span
      style={{
        fontFamily: "var(--hz-font-brand)",
        fontWeight: 500,
        letterSpacing: "0.32em",
        textTransform: "uppercase",
        color: cor,
        fontSize: Math.max(12, tamanho * 0.34),
      }}
    >
      Horizon
    </span>
  );
  const direcao = variante === "horizontal" ? "row" : "column";
  return (
    <span
      role="img"
      aria-label="Horizon"
      style={{
        display: "inline-flex",
        flexDirection: direcao,
        alignItems: "center",
        gap: 8,
      }}
    >
      <Simbolo tamanho={tamanho} prefixo={prefixo} />
      {variante === "simbolo" ? null : nome}
    </span>
  );
}
