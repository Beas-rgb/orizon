import { useEffect, useState } from "react";

const CHAVE = "orizon-design-consultora";

export type DesignTela = "atual" | "novo";

const ouvintes = new Set<() => void>();

export function lerDesignTela(): DesignTela {
  try {
    return localStorage.getItem(CHAVE) === "novo" ? "novo" : "atual";
  } catch {
    return "atual";
  }
}

export function gravarDesignTela(valor: DesignTela) {
  localStorage.setItem(CHAVE, valor);
  ouvintes.forEach((ouvir) => ouvir());
}

export function useDesignTela() {
  const [valor, setValor] = useState(lerDesignTela);
  useEffect(() => {
    const atualizar = () => setValor(lerDesignTela());
    ouvintes.add(atualizar);
    return () => {
      ouvintes.delete(atualizar);
    };
  }, []);
  return [valor, gravarDesignTela] as const;
}
