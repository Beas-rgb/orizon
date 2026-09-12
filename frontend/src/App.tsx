import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import {
  CadastroPage,
  LandingPage,
  LoginPage,
  PrimeiroAcessoPage,
  RecuperarPage,
} from "./pages/AuthPages";
import { ConsultoraDashboard } from "./pages/ConsultoraDashboard";
import { DevPainel, FuncionarioPainel, OrgaoPainel } from "./pages/Paineis";
import {
  NovoProjetoPage,
  ProjetoDetalhePage,
  ProjetosListaPage,
} from "./pages/ProjetosPages";
import { ResponderPage } from "./pages/ResponderPage";

function RequireAuth({ children }: { children: ReactNode }) {
  const { pronto, usuario } = useAuth();
  if (!pronto) {
    return (
      <div className="min-h-screen page-bg flex items-center justify-center text-gray-500 text-sm">
        Carregando…
      </div>
    );
  }
  if (!usuario) return <Navigate to="/entrar" replace />;
  return children;
}

function HomeApp() {
  const { usuario } = useAuth();
  if (usuario?.painel === "consultora") return <ConsultoraDashboard />;
  if (usuario?.painel === "orgao") return <OrgaoPainel />;
  if (usuario?.painel === "funcionario") return <FuncionarioPainel />;
  if (usuario?.painel === "dev") return <DevPainel />;
  return <Navigate to="/entrar" replace />;
}

/**
 * basename="/app" → URLs públicas: /app/, /app/entrar, /app/projetos...
 * Paths aqui NÃO repetem /app.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/entrar" element={<LoginPage />} />
      <Route path="/cadastro" element={<CadastroPage />} />
      <Route path="/recuperar" element={<RecuperarPage />} />
      <Route path="/primeiro-acesso" element={<PrimeiroAcessoPage />} />
      <Route path="/responder/:token" element={<ResponderPage />} />
      <Route path="/responder" element={<ResponderPage />} />
      <Route
        path="/inicio"
        element={
          <RequireAuth>
            <HomeApp />
          </RequireAuth>
        }
      />
      <Route
        path="/projetos"
        element={
          <RequireAuth>
            <ProjetosListaPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projetos/novo"
        element={
          <RequireAuth>
            <NovoProjetoPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projetos/:id"
        element={
          <RequireAuth>
            <ProjetoDetalhePage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
