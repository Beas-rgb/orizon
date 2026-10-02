import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  esperaReconexaoMs,
  falhaPassageira,
  guardarSessao,
  limparSessao,
  MAX_TENTATIVAS_RECONEXAO,
  painelAtual,
  sair as sairApi,
  sessaoEncerrada,
  tokenAtual,
  type Painel,
} from "../lib/api";
import { usuarioVeioNoLogin } from "../lib/sessaoEntrada";

type Usuario = { id: string; nome: string; email: string; painel: Painel };

type AuthCtx = {
  pronto: boolean;
  usuario: Usuario | null;
  conexao: "ok" | "instavel";
  recarregar: () => Promise<void>;
  entrarComTokens: (dados: {
    access_token: string;
    refresh_token?: string;
    painel?: string;
    usuario?: Usuario | null;
  }) => Promise<void>;
  sair: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

const PAPEIS = ["consultora", "orgao", "funcionario", "dev"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [pronto, setPronto] = useState(false);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [conexao, setConexao] = useState<"ok" | "instavel">("ok");
  const tentativa = useRef(0);
  const esperaId = useRef<number | null>(null);
  const montado = useRef(true);

  const recarregar = useCallback(async () => {
    const painel = painelAtual();
    if (!tokenAtual() || !PAPEIS.includes(painel)) {
      limparSessao();
      setUsuario(null);
      setConexao("ok");
      tentativa.current = 0;
      setPronto(true);
      return;
    }
    try {
      const eu = await api<Usuario>("/auth/eu");
      if (!PAPEIS.includes(eu.painel)) {
        limparSessao();
        setUsuario(null);
        setConexao("ok");
      } else {
        setUsuario(eu);
        setConexao("ok");
        tentativa.current = 0;
      }
    } catch (erro) {
      if (sessaoEncerrada(erro)) {
        limparSessao();
        setUsuario(null);
        setConexao("ok");
        tentativa.current = 0;
      } else {
        if (falhaPassageira(erro)) {
          setConexao("instavel");
          setUsuario(
            (atual) =>
              atual ?? {
                id: "",
                nome: "",
                email: "",
                painel: painel as Painel,
              },
          );
          if (tentativa.current < MAX_TENTATIVAS_RECONEXAO && montado.current) {
            tentativa.current += 1;
            const ms = esperaReconexaoMs(tentativa.current);
            if (esperaId.current !== null) window.clearTimeout(esperaId.current);
            esperaId.current = window.setTimeout(() => {
              esperaId.current = null;
              if (montado.current) void recarregar();
            }, ms);
          }
        }
      }
    } finally {
      setPronto(true);
    }
  }, []);

  useEffect(() => {
    montado.current = true;
    void recarregar();
    return () => {
      montado.current = false;
      if (esperaId.current !== null) window.clearTimeout(esperaId.current);
    };
  }, [recarregar]);

  const entrarComTokens = useCallback(
    async (dados: {
      access_token: string;
      refresh_token?: string;
      painel?: string;
      usuario?: Usuario | null;
    }) => {
      guardarSessao(dados);
      if (usuarioVeioNoLogin(dados) && dados.usuario) {
        setUsuario(dados.usuario);
        setConexao("ok");
        setPronto(true);
        return;
      }
      setPronto(false);
      await recarregar();
    },
    [recarregar],
  );

  const sair = useCallback(async () => {
    await sairApi();
    setUsuario(null);
    setConexao("ok");
  }, []);

  const value = useMemo(
    () => ({ pronto, usuario, conexao, recarregar, entrarComTokens, sair }),
    [pronto, usuario, conexao, recarregar, entrarComTokens, sair],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth fora do AuthProvider");
  return ctx;
}
