import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/brand/Logo";
import { FaixaServidor } from "../components/estado/FaixaServidor";
import { lerAvisoSessao } from "../lib/sessao";
import { api } from "../lib/api";
import { consumirRetornoResponder } from "./ResponderPage";

/** Token do e-mail: `?t=` (preferido) ou `#` (links antigos). */
function tokenDaUrl(): string {
  const params = new URLSearchParams(window.location.search);
  const query = (params.get("t") || params.get("token") || "").trim();
  if (query) return query;
  return decodeURIComponent(window.location.hash.replace(/^#/, "")).trim();
}

const inputClass =
  "mt-1.5 w-full rounded-xl px-3.5 py-3 text-[14px] outline-none";

const inputStyle = {
  background: "var(--hz-sidebar)",
  border: "1px solid var(--hz-border)",
  color: "var(--hz-auth-text)",
} as const;

function CampoSenha({
  name = "senha",
  label = "Senha",
  minLength,
  required = true,
  autoComplete = "current-password",
}: {
  name?: string;
  label?: string;
  minLength?: number;
  required?: boolean;
  autoComplete?: string;
}) {
  const [visivel, setVisivel] = useState(false);
  return (
    <label className="block text-[13px] font-medium" style={{ color: "var(--hz-auth-text-2)" }}>
      {label}
      <span className="relative mt-1.5 block">
        <input
          name={name}
          type={visivel ? "text" : "password"}
          minLength={minLength}
          required={required}
          autoComplete={autoComplete}
          className={`${inputClass} pr-11`}
          style={inputStyle}
        />
        <button
          type="button"
          className="icon-btn absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 rounded-lg"
          aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
          onClick={() => setVisivel((v) => !v)}
        >
          {visivel ? <EyeOff size={18} strokeWidth={1.75} /> : <Eye size={18} strokeWidth={1.75} />}
        </button>
      </span>
    </label>
  );
}

/** Destino pós-login seguro (mesma regra do backend). */
function nextDaUrl(): string | null {
  const raw = new URLSearchParams(window.location.search).get("next");
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return null;
  if (raw.includes("://") || raw.includes("\\")) return null;
  const path = raw.split("?")[0].split("#")[0];
  const ok = ["/inicio", "/projetos", "/responder", "/consultora"].some(
    (p) => path === p || path.startsWith(`${p}/`),
  );
  return ok ? path : null;
}

export function LoginPage() {
  const [erro, setErro] = useState(() => lerAvisoSessao());
  const [carregando, setCarregando] = useState(false);
  const { entrarComTokens, usuario, pronto } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!pronto || !usuario) return;
    const next = nextDaUrl();
    const retorno = consumirRetornoResponder();
    navigate(next || retorno || "/inicio", { replace: true });
  }, [pronto, usuario, navigate]);

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
      const next = nextDaUrl();
      const retorno = sessionStorage.getItem("horizon_responder_retorno");
      await entrarComTokens(dados);
      if (next) navigate(next);
      else if (!retorno) navigate("/inicio");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha no login");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <AuthLayout
      titulo="Entrar"
      sub="Use o e-mail da sua conta."
      rodape={
        <>
          <Link to="/recuperar" className="font-medium hover:underline" style={{ color: "var(--hz-primary-soft)" }}>
            Esqueci a senha
          </Link>
          <Link to="/cadastro" style={{ color: "var(--hz-auth-text-2)" }}>
            Solicitar acesso
          </Link>
        </>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={enviar}>
        <label className="block text-[13px] font-medium" style={{ color: "var(--hz-auth-text-2)" }}>
          Email
          <input
            name="email"
            type="email"
            required
            autoComplete="username"
            placeholder="seuemail@exemplo.com"
            className={inputClass}
            style={inputStyle}
          />
        </label>
        <CampoSenha />
        {erro ? <p className="text-[13px]" style={{ color: "var(--hz-danger)" }}>{erro}</p> : null}
        <button
          type="submit"
          disabled={carregando}
          className="w-full rounded-xl py-3.5 text-[14px] font-semibold tracking-[0.14em] disabled:opacity-60"
          style={{ background: "var(--hz-primary)", color: "var(--hz-surface)" }}
        >
          {carregando ? "ENTRANDO…" : "ENTRAR"}
        </button>
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
      titulo="Pedir conta"
      sub="A consultora só entra depois da autorização do TI."
      rodape={
        <Link to="/entrar" className="hover:underline" style={{ color: "var(--hz-auth-text-2)" }}>
          Já tenho conta
        </Link>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={enviar}>
        <label className="block text-[13px] font-medium" style={{ color: "var(--hz-auth-text-2)" }}>
          Nome
          <input name="nome" required className={inputClass} style={inputStyle} />
        </label>
        <label className="block text-[13px] font-medium" style={{ color: "var(--hz-auth-text-2)" }}>
          E-mail
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            className={inputClass}
            style={inputStyle}
          />
        </label>
        {erro ? <p className="text-[13px] -mt-2" style={{ color: "var(--hz-danger)" }}>{erro}</p> : null}
        {ok ? <p className="text-[13px] text-[#1E7A4A] -mt-2">{ok}</p> : null}
        <button
          type="submit"
          disabled={carregando}
          className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold disabled:opacity-60 mt-1"
          style={{ background: "var(--hz-primary)", color: "var(--hz-surface)" }}
        >
          {carregando ? "Enviando…" : "Enviar pedido"}
        </button>
      </form>
    </AuthLayout>
  );
}

export function RecuperarPage() {
  const [erro, setErro] = useState("");
  const [ok, setOk] = useState("");
  const [token, setToken] = useState(() => tokenDaUrl());
  const navigate = useNavigate();
  const comToken = Boolean(token);

  async function pedirEmail(evento: FormEvent<HTMLFormElement>) {
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

  async function redefinir(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro("");
    setOk("");
    const form = evento.currentTarget;
    try {
      await api("/auth/redefinir-senha", {
        method: "POST",
        json: {
          token: token.trim(),
          senha: (form.elements.namedItem("senha") as HTMLInputElement).value,
        },
      });
      setOk("Senha redefinida. Entre com a nova senha.");
      setTimeout(() => navigate("/entrar"), 1200);
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha");
    }
  }

  if (comToken) {
    return (
      <AuthLayout
        titulo="Nova senha"
        sub="Mínimo 8 caracteres, com maiúscula, número e símbolo."
        rodape={
          <Link to="/entrar" className="hover:underline" style={{ color: "var(--hz-auth-text-2)" }}>
            Voltar ao login
          </Link>
        }
      >
        <form className="flex flex-col gap-5" onSubmit={redefinir}>
          <label className="block text-[13px] font-medium" style={{ color: "var(--hz-auth-text-2)" }}>
            Token
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
              className={inputClass}
              style={inputStyle}
            />
          </label>
          <CampoSenha label="Nova senha" minLength={8} autoComplete="new-password" />
          {erro ? <p className="text-[13px] -mt-2" style={{ color: "var(--hz-danger)" }}>{erro}</p> : null}
          {ok ? <p className="text-[13px] text-[#1E7A4A] -mt-2">{ok}</p> : null}
          <button
            type="submit"
            className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold mt-1"
            style={{ background: "var(--hz-primary)", color: "var(--hz-surface)" }}
          >
            Salvar senha
          </button>
        </form>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      titulo="Recuperar senha"
      sub="Enviamos o link para o e-mail da conta."
      rodape={
        <Link to="/entrar" className="hover:underline" style={{ color: "var(--hz-auth-text-2)" }}>
          Voltar ao login
        </Link>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={pedirEmail}>
        <label className="block text-[13px] font-medium" style={{ color: "var(--hz-auth-text-2)" }}>
          E-mail
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            className={inputClass}
            style={inputStyle}
          />
        </label>
        {erro ? <p className="text-[13px] -mt-2" style={{ color: "var(--hz-danger)" }}>{erro}</p> : null}
        {ok ? <p className="text-[13px] text-[#1E7A4A] -mt-2">{ok}</p> : null}
        <button
          type="submit"
          className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold mt-1"
          style={{ background: "var(--hz-primary)", color: "var(--hz-surface)" }}
        >
          Enviar instruções
        </button>
      </form>
    </AuthLayout>
  );
}

export function PrimeiroAcessoPage() {
  const [erro, setErro] = useState("");
  const [token, setToken] = useState(() => tokenDaUrl());
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
      navigate("/inicio");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha");
    }
  }

  return (
    <AuthLayout
      titulo="Primeiro acesso"
      sub="Cole o token do convite e escolha sua senha."
      rodape={
        <Link to="/entrar" className="hover:underline" style={{ color: "var(--hz-auth-text-2)" }}>
          Já defini minha senha
        </Link>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={enviar}>
        <label className="block text-[13px] font-medium" style={{ color: "var(--hz-auth-text-2)" }}>
          Token do convite
          <input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            required
            autoComplete="off"
            className={inputClass}
            style={inputStyle}
            placeholder="Cole aqui o código do e-mail"
          />
        </label>
        <CampoSenha
          label="Criar senha"
          minLength={8}
          autoComplete="new-password"
        />
        <p className="text-[12px] -mt-2 leading-relaxed" style={{ color: "var(--hz-auth-text-2)" }}>
          Use no mínimo 8 caracteres, com letra maiúscula, número e símbolo.
        </p>
        {erro ? <p className="text-[13px]" style={{ color: "var(--hz-danger)" }}>{erro}</p> : null}
        <button
          type="submit"
          className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold mt-1"
          style={{ background: "var(--hz-primary)", color: "var(--hz-surface)" }}
        >
          Continuar
        </button>
      </form>
    </AuthLayout>
  );
}

/** Home pública — antes do login. */
export function LandingPage() {
  const { pronto, usuario } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (pronto && usuario) navigate("/inicio", { replace: true });
  }, [pronto, usuario, navigate]);

  return (
    <div
      className="relative min-h-screen overflow-hidden"
      style={{ background: "var(--hz-auth-bg)", color: "var(--hz-auth-text)" }}
    >
      <FaixaServidor />
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 50% at 15% 20%, rgba(29,95,175,0.10), transparent 55%), radial-gradient(ellipse 50% 40% at 90% 80%, rgba(22,74,138,0.07), transparent 50%)",
        }}
      />

      <header className="relative z-10 flex items-center justify-between px-6 sm:px-10 py-6 max-w-5xl mx-auto w-full">
        <Link to="/" className="flex items-center gap-2.5">
          <Logo variante="horizontal" tamanho={28} tom="escuro" />
        </Link>
        <Link
          to="/entrar"
          className="px-3 py-2 text-[13px] font-semibold"
          style={{ color: "var(--hz-auth-text)" }}
        >
          Entrar
        </Link>
      </header>

      <main className="relative z-10 max-w-5xl mx-auto px-6 sm:px-10 pt-16 sm:pt-24 pb-20">
        <p
          className="text-[13px] font-semibold tracking-[0.18em] uppercase mb-5"
          style={{ color: "var(--hz-primary-soft)" }}
        >
          Horizon
        </p>
        <h1 className="max-w-xl text-[2.75rem] font-semibold leading-[1.08] tracking-tight sm:text-6xl">
          Pesquisas com clareza para cada papel.
        </h1>
        <p className="mt-6 max-w-md text-[16px] leading-relaxed sm:text-[17px]" style={{ color: "var(--hz-auth-text-2)" }}>
          A consultora aplica. O funcionário responde. O órgão vê o consolidado.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row gap-3 sm:items-center">
          <Link
            to="/entrar"
            className="inline-flex justify-center px-7 py-3.5 rounded-xl text-white text-[14px] font-semibold"
            style={{ background: "var(--hz-primary)" }}
          >
            Entrar
          </Link>
          <Link
            to="/primeiro-acesso"
            className="inline-flex justify-center rounded-xl px-7 py-3.5 text-[14px] font-semibold"
            style={{
              background: "var(--hz-auth-card)",
              color: "var(--hz-auth-text)",
              border: "1px solid var(--hz-border)",
            }}
          >
            Primeiro acesso
          </Link>
        </div>

        <p className="mt-8 text-[13px]" style={{ color: "var(--hz-auth-text-2)" }}>
          Consultora sem conta?{" "}
          <Link to="/cadastro" className="font-medium hover:underline" style={{ color: "var(--hz-primary-soft)" }}>
            Pedir acesso
          </Link>
        </p>
      </main>
    </div>
  );
}

function AuthLayout({
  titulo,
  sub,
  children,
  rodape,
}: {
  titulo: string;
  sub: string;
  children: ReactNode;
  rodape?: ReactNode;
}) {
  return (
    <div
      className="flex min-h-dvh flex-col"
      style={{ background: "var(--hz-auth-bg)", color: "var(--hz-auth-text)" }}
    >
      <FaixaServidor />
      <div className="flex flex-1 flex-col items-center justify-center px-5 py-10">
        <Logo variante="empilhado" tamanho={64} tom="escuro" />
        <p
          className="mt-3 text-[11px]"
          style={{ letterSpacing: "0.28em", color: "var(--hz-auth-text-2)" }}
        >
          DADOS • PESSOAS • RESULTADOS
        </p>
        <div
          className="mt-8 w-full max-w-[400px] rounded-2xl p-6 sm:p-7"
          style={{
            background: "var(--hz-auth-card)",
            border: "1px solid var(--hz-border)",
          }}
        >
          <h1 className="text-[22px] font-medium tracking-tight">{titulo}</h1>
          <p className="mt-2 text-[14px] leading-relaxed" style={{ color: "var(--hz-auth-text-2)" }}>
            {sub}
          </p>
          <div className="mt-6">{children}</div>
          {rodape ? (
            <div className="mt-6 flex flex-wrap items-center justify-between gap-3 text-[13px]">
              {rodape}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
