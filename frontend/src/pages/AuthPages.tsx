import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { ACCENT, glassStyle } from "../lib/theme";

export function LoginPage() {
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const { entrarComTokens } = useAuth();
  const navigate = useNavigate();

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    setCarregando(true);
    const form = evento.currentTarget;
    try {
      const dados = await api<{
        access_token: string;
        refresh_token?: string;
        painel?: string;
      }>("/auth/login", {
        method: "POST",
        json: {
          email: (form.elements.namedItem("email") as HTMLInputElement).value,
          senha: (form.elements.namedItem("senha") as HTMLInputElement).value,
        },
      });
      if (!["consultora", "orgao", "funcionario", "dev"].includes(dados.painel || "")) {
        setErro("Este acesso não abre painel.");
        return;
      }
      await entrarComTokens(dados);
      navigate("/app");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha no login");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <AuthLayout
      titulo="Entrar"
      sub="A tela abre conforme a conta: consultora, órgão, funcionário ou desenvolvimento."
    >
      <form className="flex flex-col gap-3" onSubmit={enviar}>
        <label className="text-[12px] font-semibold text-gray-600">
          E-mail
          <input
            name="email"
            type="email"
            required
            className="mt-1 w-full rounded-xl px-3 py-2.5 outline-none"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          />
        </label>
        <label className="text-[12px] font-semibold text-gray-600">
          Senha
          <input
            name="senha"
            type="password"
            required
            className="mt-1 w-full rounded-xl px-3 py-2.5 outline-none"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          />
        </label>
        {erro ? <p className="text-[13px] text-[#A02828]">{erro}</p> : null}
        <button
          type="submit"
          disabled={carregando}
          className="rounded-2xl py-3 text-white text-[14px] font-bold mt-1 disabled:opacity-60"
          style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
        >
          {carregando ? "Entrando…" : "Entrar"}
        </button>
        <div className="flex flex-wrap gap-3 text-[12px] justify-between mt-1">
          <Link to="/recuperar" className="text-[#1D5FAF] font-semibold">
            Esqueci a senha
          </Link>
          <Link to="/cadastro" className="text-gray-600">
            Pedir conta de consultora
          </Link>
        </div>
        <Link to="/" className="text-center text-[12px] text-gray-500 mt-2">
          Voltar
        </Link>
      </form>
    </AuthLayout>
  );
}

export function CadastroPage() {
  const [erro, setErro] = useState("");
  const [ok, setOk] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    setOk("");
    setCarregando(true);
    const form = evento.currentTarget;
    try {
      const resp = await api<{ mensagem: string }>("/auth/cadastro-consultora", {
        method: "POST",
        json: {
          nome: (form.elements.namedItem("nome") as HTMLInputElement).value,
          email: (form.elements.namedItem("email") as HTMLInputElement).value,
        },
      });
      setOk(resp.mensagem || "Pedido enviado. O TI autoriza antes da conta nascer.");
      form.reset();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha no cadastro");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <AuthLayout
      titulo="Cadastro da consultora"
      sub="Cria um pedido PENDENTE. Só o TI autoriza; a senha nasce no primeiro acesso."
    >
      <form className="flex flex-col gap-3" onSubmit={enviar}>
        <label className="text-[12px] font-semibold text-gray-600">
          Nome
          <input
            name="nome"
            required
            className="mt-1 w-full rounded-xl px-3 py-2.5 outline-none"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          />
        </label>
        <label className="text-[12px] font-semibold text-gray-600">
          E-mail
          <input
            name="email"
            type="email"
            required
            className="mt-1 w-full rounded-xl px-3 py-2.5 outline-none"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          />
        </label>
        {erro ? <p className="text-[13px] text-[#A02828]">{erro}</p> : null}
        {ok ? <p className="text-[13px] text-[#1E7A4A]">{ok}</p> : null}
        <button
          type="submit"
          disabled={carregando}
          className="rounded-2xl py-3 text-white text-[14px] font-bold mt-1 disabled:opacity-60"
          style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
        >
          {carregando ? "Enviando…" : "Enviar pedido"}
        </button>
        <Link to="/entrar" className="text-center text-[12px] text-gray-500 mt-2">
          Já tenho conta
        </Link>
      </form>
    </AuthLayout>
  );
}

export function RecuperarPage() {
  const [erro, setErro] = useState("");
  const [ok, setOk] = useState("");

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    setOk("");
    const form = evento.currentTarget;
    try {
      const resp = await api<{ mensagem: string }>("/auth/recuperar-senha", {
        method: "POST",
        json: { email: (form.elements.namedItem("email") as HTMLInputElement).value },
      });
      setOk(resp.mensagem || "Se o e-mail existir, as instruções foram enviadas.");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha");
    }
  }

  return (
    <AuthLayout
      titulo="Esqueci a senha"
      sub="O link vai para o e-mail de acesso. A senha nunca vem no e-mail."
    >
      <form className="flex flex-col gap-3" onSubmit={enviar}>
        <label className="text-[12px] font-semibold text-gray-600">
          E-mail
          <input
            name="email"
            type="email"
            required
            className="mt-1 w-full rounded-xl px-3 py-2.5 outline-none"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          />
        </label>
        {erro ? <p className="text-[13px] text-[#A02828]">{erro}</p> : null}
        {ok ? <p className="text-[13px] text-[#1E7A4A]">{ok}</p> : null}
        <button
          type="submit"
          className="rounded-2xl py-3 text-white text-[14px] font-bold mt-1"
          style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
        >
          Enviar instruções
        </button>
        <Link to="/entrar" className="text-center text-[12px] text-gray-500 mt-2">
          Voltar ao login
        </Link>
      </form>
    </AuthLayout>
  );
}

export function PrimeiroAcessoPage() {
  const [erro, setErro] = useState("");
  const [token, setToken] = useState(() =>
    decodeURIComponent(window.location.hash.replace(/^#/, "")).trim(),
  );
  const { entrarComTokens } = useAuth();
  const navigate = useNavigate();

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    const form = evento.currentTarget;
    try {
      const dados = await api<{
        access_token: string;
        refresh_token?: string;
        painel?: string;
      }>("/auth/primeiro-acesso", {
        method: "POST",
        json: {
          token: token.trim(),
          senha: (form.elements.namedItem("senha") as HTMLInputElement).value,
        },
      });
      await entrarComTokens(dados);
      navigate("/app");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha");
    }
  }

  return (
    <AuthLayout
      titulo="Primeiro acesso"
      sub="Cole o token do convite e defina a senha (mín. 8, maiúscula, número e especial)."
    >
      <form className="flex flex-col gap-3" onSubmit={enviar}>
        <label className="text-[12px] font-semibold text-gray-600">
          Token
          <input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            required
            className="mt-1 w-full rounded-xl px-3 py-2.5 outline-none"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          />
        </label>
        <label className="text-[12px] font-semibold text-gray-600">
          Senha
          <input
            name="senha"
            type="password"
            minLength={8}
            required
            className="mt-1 w-full rounded-xl px-3 py-2.5 outline-none"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          />
        </label>
        {erro ? <p className="text-[13px] text-[#A02828]">{erro}</p> : null}
        <button
          type="submit"
          className="rounded-2xl py-3 text-white text-[14px] font-bold mt-1"
          style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
        >
          Definir senha
        </button>
        <Link to="/entrar" className="text-center text-[12px] text-gray-500 mt-2">
          Voltar
        </Link>
      </form>
    </AuthLayout>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-screen page-bg relative overflow-hidden">
      <div
        className="absolute pointer-events-none"
        style={{
          top: "-120px",
          right: "-80px",
          width: "480px",
          height: "480px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(29,95,175,0.12) 0%, transparent 70%)",
          filter: "blur(40px)",
        }}
      />
      <header className="relative z-10 flex items-center justify-between px-5 sm:px-8 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div
            className="w-9 h-9 rounded-2xl flex items-center justify-center text-white text-sm font-bold"
            style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
          >
            OR
          </div>
          <div>
            <p className="font-bold text-gray-800 text-sm">Orizon</p>
            <p className="text-[11px] text-gray-500">Horizon</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            to="/primeiro-acesso"
            className="hidden sm:inline-flex px-4 py-2 rounded-xl text-[13px] font-semibold text-gray-700"
            style={{ background: "rgba(255,255,255,0.55)", border: "1px solid rgba(255,255,255,0.7)" }}
          >
            Primeiro acesso
          </Link>
          <Link
            to="/entrar"
            className="px-4 py-2 rounded-xl text-[13px] font-bold text-white"
            style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
          >
            Entrar
          </Link>
        </div>
      </header>
      <main className="relative z-10 max-w-6xl mx-auto px-5 sm:px-8 pt-10 sm:pt-20 pb-16">
        <p className="text-[11px] font-bold tracking-[0.2em] uppercase text-[#1D5FAF] mb-4">
          Consultoria · Pesquisa
        </p>
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-gray-900 leading-[1.05] max-w-3xl">
          Orizon
        </h1>
        <p className="mt-4 text-lg sm:text-xl text-gray-600 max-w-xl leading-relaxed">
          A consultora aplica a pesquisa, o funcionário responde e vê a própria nota, o órgão
          consulta o resultado.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/entrar"
            className="px-6 py-3 rounded-2xl text-white text-[14px] font-bold"
            style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
          >
            Entrar no painel
          </Link>
          <Link
            to="/cadastro"
            className="px-6 py-3 rounded-2xl text-[14px] font-semibold text-gray-700"
            style={glassStyle}
          >
            Pedir conta de consultora
          </Link>
        </div>
      </main>
    </div>
  );
}

function AuthLayout({
  titulo,
  sub,
  children,
}: {
  titulo: string;
  sub: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen page-bg flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-3xl p-6 sm:p-8" style={glassStyle}>
        <div className="flex items-center gap-3 mb-5">
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center text-white font-bold"
            style={{ background: `linear-gradient(135deg, ${ACCENT}, #164A8A)` }}
          >
            OR
          </div>
          <div>
            <p className="font-bold text-gray-800">{titulo}</p>
            <p className="text-[12px] text-gray-500 leading-snug">{sub}</p>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}
