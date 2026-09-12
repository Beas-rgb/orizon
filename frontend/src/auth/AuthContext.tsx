import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  guardarSessao,
  limparSessao,
  painelAtual,
  sair as sairApi,
  tokenAtual,
  type Painel,
} from "../lib/api";

type Usuario = { id: string; nome: string; email: string; painel: Painel };

type AuthCtx = {
  pronto: boolean;
  usuario: Usuario | null;
  recarregar: () => Promise<void>;
  entrarComTokens: (dados: {
    access_token: string;
    refresh_token?: string;
    painel?: string;
  }) => Promise<void>;
  sair: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [pronto, setPronto] = useState(false);
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  const recarregar = useCallback(async () => {
    const painel = painelAtual();
    if (!tokenAtual() || !["consultora", "orgao", "funcionario", "dev"].includes(painel)) {
      limparSessao();
      setUsuario(null);
      setPronto(true);
      return;
    }
    try {
      const eu = await api<Usuario>("/auth/eu");
      if (!["consultora", "orgao", "funcionario", "dev"].includes(eu.painel)) {
        limparSessao();
        setUsuario(null);
      } else {
        setUsuario(eu);
      }
    } catch {
      limparSessao();
      setUsuario(null);
    } finally {
      setPronto(true);
    }
  }, []);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  const entrarComTokens = useCallback(
    async (dados: { access_token: string; refresh_token?: string; painel?: string }) => {
      guardarSessao(dados);
      setPronto(false);
      await recarregar();
    },
    [recarregar],
  );

  const sair = useCallback(async () => {
    await sairApi();
    setUsuario(null);
  }, []);

  const value = useMemo(
    () => ({ pronto, usuario, recarregar, entrarComTokens, sair }),
    [pronto, usuario, recarregar, entrarComTokens, sair],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}
