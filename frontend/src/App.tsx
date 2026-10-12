import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import {
  CadastroPage,
  LandingPage,
  LoginPage,
  PrimeiroAcessoPage,
  RecuperarPage,
} from "./pages/AuthPages";

const ConsultoraDashboard = lazy(() =>
  import("./pages/ConsultoraDashboard").then((m) => ({ default: m.ConsultoraDashboard })),
);
const ConsultoraPesquisasPage = lazy(() =>
  import("./pages/ConsultoraPesquisasPage").then((m) => ({
    default: m.ConsultoraPesquisasPage,
  })),
);
const ConsultoraPesquisasTestePage = lazy(() =>
  import("./pages/ConsultoraPesquisasTestePage").then((m) => ({
    default: m.ConsultoraPesquisasTestePage,
  })),
);
const LabPage = lazy(() =>
  import("./pages/LabPage").then((m) => ({ default: m.LabPage })),
);
const DevPainel = lazy(() =>
  import("./pages/Paineis").then((m) => ({ default: m.DevPainel })),
);
const FuncionarioPainel = lazy(() =>
  import("./pages/Paineis").then((m) => ({ default: m.FuncionarioPainel })),
);
const OrgaoPainel = lazy(() =>
  import("./pages/Paineis").then((m) => ({ default: m.OrgaoPainel })),
);
const PesquisaEditorPage = lazy(() =>
  import("./pages/PesquisaEditorPage").then((m) => ({ default: m.PesquisaEditorPage })),
);
const NovoProjetoPage = lazy(() =>
  import("./pages/ProjetosPages").then((m) => ({ default: m.NovoProjetoPage })),
);
const ProjetoDetalhePage = lazy(() =>
  import("./pages/ProjetosPages").then((m) => ({ default: m.ProjetoDetalhePage })),
);
const ProjetosListaPage = lazy(() =>
  import("./pages/ProjetosPages").then((m) => ({ default: m.ProjetosListaPage })),
);
const ResponderPage = lazy(() =>
  import("./pages/ResponderPage").then((m) => ({ default: m.ResponderPage })),
);
const Pagina404 = lazy(() =>
  import("./ui/EstadosTela").then((m) => ({ default: m.Pagina404 })),
);
const MinhaContaPage = lazy(() =>
  import("./pages/ContaNotasPages").then((m) => ({ default: m.MinhaContaPage })),
);
const MinhasNotasPage = lazy(() =>
  import("./pages/ContaNotasPages").then((m) => ({ default: m.MinhasNotasPage })),
);
const NotificacoesPage = lazy(() =>
  import("./pages/ContaNotasPages").then((m) => ({ default: m.NotificacoesPage })),
);
const DocumentosPage = lazy(() =>
  import("./pages/ContaNotasPages").then((m) => ({ default: m.DocumentosPage })),
);
const BancoPerguntasPage = lazy(() =>
  import("./pages/ContaNotasPages").then((m) => ({ default: m.BancoPerguntasPage })),
);

function Espera({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm" style={{ background: "var(--hz-bg)", color: "var(--hz-text-2)" }}>
          Carregando…
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { pronto, usuario } = useAuth();
  if (!pronto) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm" style={{ background: "var(--hz-bg)", color: "var(--hz-text-2)" }}>
        Carregando…
      </div>
    );
  }
  if (!usuario) return <Navigate to="/" replace />;
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
 * basename="/app") → URLs públicas: /app/, /app/entrar, /app/projetos...
 * Paths aqui NÃO repetem /app.
 */
export default function App() {
  return (
    <Espera>
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/entrar" element={<LoginPage />} />
      <Route path="/cadastro" element={<CadastroPage />} />
      <Route path="/recuperar" element={<RecuperarPage />} />
      <Route path="/primeiro-acesso" element={<PrimeiroAcessoPage />} />
      <Route path="/responder/pesquisa/:pesquisaId" element={<ResponderPage />} />
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
      <Route
        path="/projetos/:projetoId/pesquisas/:pesquisaId"
        element={
          <RequireAuth>
            <PesquisaEditorPage />
          </RequireAuth>
        }
      />
      <Route
        path="/consultora/pesquisas"
        element={
          <RequireAuth>
            <ConsultoraPesquisasPage />
          </RequireAuth>
        }
      />
      <Route
        path="/consultora/pesquisas-teste"
        element={
          <RequireAuth>
            <ConsultoraPesquisasTestePage />
          </RequireAuth>
        }
      />
      <Route
        path="/lab"
        element={
          <RequireAuth>
            <LabPage />
          </RequireAuth>
        }
      />
      <Route
        path="/conta"
        element={
          <RequireAuth>
            <MinhaContaPage />
          </RequireAuth>
        }
      />
      <Route
        path="/minhas-notas"
        element={
          <RequireAuth>
            <MinhasNotasPage />
          </RequireAuth>
        }
      />
      <Route
        path="/notificacoes"
        element={
          <RequireAuth>
            <NotificacoesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/documentos"
        element={
          <RequireAuth>
            <DocumentosPage />
          </RequireAuth>
        }
      />
      <Route
        path="/biblioteca"
        element={
          <RequireAuth>
            <DocumentosPage />
          </RequireAuth>
        }
      />
      <Route
        path="/banco-perguntas"
        element={
          <RequireAuth>
            <BancoPerguntasPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Pagina404 />} />
    </Routes>
    </Espera>
  );
}
