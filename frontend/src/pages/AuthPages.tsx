import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { ACCENT, ACCENT_DARK } from "../lib/theme";
import { consumirRetornoResponder } from "./ResponderPage";

const inputClass =
  "mt-1.5 w-full rounded-xl px-3.5 py-3 text-[14px] text-gray-800 outline-none transition-[border,box-shadow] focus:border-[#1D5FAF]/55 focus:shadow-[0_0_0_3px_rgba(29,95,175,0.12)]";

const inputStyle = {
  background: "rgba(255,255,255,0.82)",
  border: "1px solid rgba(220,226,235,0.95)",
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
    <label className="block text-[13px] font-medium text-gray-600">
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
          className="icon-btn absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-black/5"
          aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
          onClick={() => setVisivel((v) => !v)}
        >
          {visivel ? <EyeOff size={18} strokeWidth={1.75} /> : <Eye size={18} strokeWidth={1.75} />}
        </button>
      </span>
    </label>
  );
}

export function LoginPage() {
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const { entrarComTokens, usuario, pronto } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!pronto || !usuario) return;
    const retorno = consumirRetornoResponder();
    navigate(retorno || "/inicio", { replace: true });
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
      const retorno = sessionStorage.getItem("horizon_responder_retorno");
      await entrarComTokens(dados);
      if (!retorno) navigate("/inicio");
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
          <Link to="/recuperar" className="text-[#1D5FAF] font-medium hover:underline">
            Esqueci a senha
          </Link>
          <Link to="/primeiro-acesso" className="text-gray-500 hover:text-gray-700">
            Primeiro acesso
          </Link>
        </>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={enviar}>
        <label className="block text-[13px] font-medium text-gray-600">
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
        <CampoSenha />
        {erro ? <p className="text-[13px] text-[#A02828] -mt-2">{erro}</p> : null}
        <button
          type="submit"
          disabled={carregando}
          className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold disabled:opacity-60 mt-1"
          style={{ background: ACCENT }}
        >
          {carregando ? "Entrando…" : "Entrar"}
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
        <Link to="/entrar" className="text-gray-500 hover:text-gray-700">
          Já tenho conta
        </Link>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={enviar}>
        <label className="block text-[13px] font-medium text-gray-600">
          Nome
          <input name="nome" required className={inputClass} style={inputStyle} />
        </label>
        <label className="block text-[13px] font-medium text-gray-600">
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
        {erro ? <p className="text-[13px] text-[#A02828] -mt-2">{erro}</p> : null}
        {ok ? <p className="text-[13px] text-[#1E7A4A] -mt-2">{ok}</p> : null}
        <button
          type="submit"
          disabled={carregando}
          className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold disabled:opacity-60 mt-1"
          style={{ background: ACCENT }}
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
  const [token, setToken] = useState(() =>
    decodeURIComponent(window.location.hash.replace(/^#/, "")).trim(),
  );
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
          <Link to="/entrar" className="text-gray-500 hover:text-gray-700">
            Voltar ao login
          </Link>
        }
      >
        <form className="flex flex-col gap-5" onSubmit={redefinir}>
          <label className="block text-[13px] font-medium text-gray-600">
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
          {erro ? <p className="text-[13px] text-[#A02828] -mt-2">{erro}</p> : null}
          {ok ? <p className="text-[13px] text-[#1E7A4A] -mt-2">{ok}</p> : null}
          <button
            type="submit"
            className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold mt-1"
            style={{ background: ACCENT }}
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
        <Link to="/entrar" className="text-gray-500 hover:text-gray-700">
          Voltar ao login
        </Link>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={pedirEmail}>
        <label className="block text-[13px] font-medium text-gray-600">
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
        {erro ? <p className="text-[13px] text-[#A02828] -mt-2">{erro}</p> : null}
        {ok ? <p className="text-[13px] text-[#1E7A4A] -mt-2">{ok}</p> : null}
        <button
          type="submit"
          className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold mt-1"
          style={{ background: ACCENT }}
        >
          Enviar instruções
        </button>
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
        <Link to="/entrar" className="text-gray-500 hover:text-gray-700">
          Já defini minha senha
        </Link>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={enviar}>
        <label className="block text-[13px] font-medium text-gray-600">
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
        <p className="text-[12px] text-gray-500 -mt-2 leading-relaxed">
          Use no mínimo 8 caracteres, com letra maiúscula, número e símbolo.
        </p>
        {erro ? <p className="text-[13px] text-[#A02828]">{erro}</p> : null}
        <button
          type="submit"
          className="w-full rounded-xl py-3.5 text-white text-[14px] font-semibold mt-1"
          style={{ background: ACCENT }}
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
    <div className="min-h-screen relative overflow-hidden page-bg">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 50% at 15% 20%, rgba(29,95,175,0.10), transparent 55%), radial-gradient(ellipse 50% 40% at 90% 80%, rgba(22,74,138,0.07), transparent 50%)",
        }}
      />

      <header className="relative z-10 flex items-center justify-between px-6 sm:px-10 py-6 max-w-5xl mx-auto w-full">
        <Link to="/" className="flex items-center gap-2.5">
          <span
            className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-[12px] font-bold tracking-wide"
            style={{ background: ACCENT }}
          >
            OR
          </span>
          <span className="text-[15px] font-semibold text-gray-900 tracking-tight">Orizon</span>
        </Link>
        <Link
          to="/entrar"
          className="text-[13px] font-semibold text-gray-700 hover:text-gray-900 px-3 py-2"
        >
          Entrar
        </Link>
      </header>

      <main className="relative z-10 max-w-5xl mx-auto px-6 sm:px-10 pt-16 sm:pt-24 pb-20">
        <p
          className="text-[13px] font-semibold tracking-[0.18em] uppercase mb-5"
          style={{ color: ACCENT }}
        >
          Orizon
        </p>
        <h1 className="text-[2.75rem] sm:text-6xl font-semibold text-gray-900 tracking-tight leading-[1.08] max-w-xl">
          Pesquisas com clareza para cada papel.
        </h1>
        <p className="mt-6 text-[16px] sm:text-[17px] text-gray-600 max-w-md leading-relaxed">
          A consultora aplica. O funcionário responde. O órgão vê o consolidado.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row gap-3 sm:items-center">
          <Link
            to="/entrar"
            className="inline-flex justify-center px-7 py-3.5 rounded-xl text-white text-[14px] font-semibold"
            style={{ background: ACCENT }}
          >
            Entrar
          </Link>
          <Link
            to="/primeiro-acesso"
            className="inline-flex justify-center px-7 py-3.5 rounded-xl text-[14px] font-semibold text-gray-800"
            style={{
              background: "rgba(255,255,255,0.65)",
              border: "1px solid rgba(210,218,230,0.9)",
            }}
          >
            Primeiro acesso
          </Link>
        </div>

        <p className="mt-8 text-[13px] text-gray-500">
          Consultora sem conta?{" "}
          <Link to="/cadastro" className="font-medium text-[#1D5FAF] hover:underline">
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
    <div className="min-h-screen page-bg flex flex-col">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 60% 45% at 50% 0%, rgba(29,95,175,0.08), transparent 60%)",
        }}
      />
      <header className="relative z-10 px-6 sm:px-10 py-6 max-w-lg mx-auto w-full">
        <Link to="/" className="inline-flex items-center gap-2.5">
          <span
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-[11px] font-bold"
            style={{ background: ACCENT_DARK }}
          >
            OR
          </span>
          <span className="text-[14px] font-semibold text-gray-900">Orizon</span>
        </Link>
      </header>

      <div className="relative z-10 flex-1 flex items-start sm:items-center justify-center px-5 pb-12">
        <div className="w-full max-w-[400px]">
          <h1 className="text-[26px] sm:text-[28px] font-semibold text-gray-900 tracking-tight">
            {titulo}
          </h1>
          <p className="mt-2 text-[14px] text-gray-500 leading-relaxed">{sub}</p>

          <div
            className="mt-8 rounded-2xl p-6 sm:p-7"
            style={{
              background: "rgba(255,255,255,0.72)",
              border: "1px solid rgba(255,255,255,0.85)",
              boxShadow: "0 12px 40px rgba(15, 35, 70, 0.06)",
            }}
          >
            {children}
          </div>

          {rodape ? (
            <div className="mt-6 flex flex-wrap items-center justify-between gap-3 text-[13px]">
              {rodape}
            </div>
          ) : null}

          <p className="mt-8 text-center">
            <Link to="/" className="text-[12px] text-gray-400 hover:text-gray-600">
              ← Voltar à página inicial
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
