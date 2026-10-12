/**
 * Laboratório mínimo. Sem design system — refeita na Fase 7.
 * Só aparece com usuario.lab_habilitado.
 */
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/layout/AppShell";
import { api } from "../lib/api";

type Cenario = {
  id: string;
  nome: string;
  tipo: string;
  tamanho: number;
  seed: number;
  perfil: string;
  status: string;
  projeto_id: string | null;
  progresso: number;
  erro: string | null;
};

export function LabPage() {
  const { usuario } = useAuth();
  const [lista, setLista] = useState<Cenario[]>([]);
  const [erro, setErro] = useState("");
  const [nome, setNome] = useState("Cenario lab");
  const [tamanho, setTamanho] = useState(100);
  const [tipo, setTipo] = useState("CLIMA");
  const [perfil, setPerfil] = useState("NEUTRO");
  const [confirmar, setConfirmar] = useState<Record<string, string>>({});
  const [ocupado, setOcupado] = useState(false);
  const [previa, setPrevia] = useState("");
  const [area, setArea] = useState("visao");
  const [conviteModo, setConviteModo] = useState("SIMULADO");
  const [limites, setLimites] = useState<{ max_participantes: number } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const dados = await api<Cenario[]>("/lab/cenarios");
      setLista(dados);
      setLimites(await api<{ max_participantes: number }>("/lab/limites"));
      setErro("");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha ao listar.");
    }
  }, []);

  useEffect(() => {
    if (!usuario?.lab_habilitado) return;
    void carregar();
    const id = window.setInterval(() => {
      void carregar();
    }, 3000);
    return () => window.clearInterval(id);
  }, [usuario?.lab_habilitado, carregar]);

  if (!usuario?.lab_habilitado) {
    return (
      <main style={{ padding: 24 }}>
        <p>Laboratório indisponível.</p>
        <Link to="/inicio">Voltar</Link>
      </main>
    );
  }

  async function criar(ev: FormEvent) {
    ev.preventDefault();
    setOcupado(true);
    try {
      await api("/lab/cenarios", {
        method: "POST",
        json: { nome, tipo, tamanho, perfil, seed: Date.now() % 1_000_000 },
      });
      await carregar();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha ao criar.");
    } finally {
      setOcupado(false);
    }
  }

  async function convidar(id: string, ev: FormEvent) {
    ev.preventDefault();
    const form = ev.currentTarget as HTMLFormElement;
    setOcupado(true);
    try {
      const resp = await api<{ modo: string; enviado: boolean }>(
        `/lab/cenarios/${id}/convites`,
        {
          method: "POST",
          json: {
            nome: (form.elements.namedItem("nome_convite") as HTMLInputElement).value,
            email: (form.elements.namedItem("email_convite") as HTMLInputElement).value,
            papel: "FUNCIONARIO",
            modo: conviteModo,
            autorizo_envio: conviteModo === "REAL",
          },
        },
      );
      setPrevia(
        resp.enviado
          ? "Convite real encaminhado ao fluxo de e-mail."
          : "Convite simulado. Nenhum e-mail real foi enviado.",
      );
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha no convite.");
    } finally {
      setOcupado(false);
    }
  }

  async function respostas(id: string) {
    setOcupado(true);
    try {
      await api(`/lab/cenarios/${id}/respostas`, {
        method: "POST",
        json: { perfil, taxa: 1, seed: Date.now() % 1_000_000 },
      });
      await carregar();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha ao gerar respostas.");
    } finally {
      setOcupado(false);
    }
  }

  async function entrarOrgao(id: string) {
    setOcupado(true);
    try {
      const tokens = await api<{ access_token: string; refresh_token: string; painel: string }>(
        `/lab/cenarios/${id}/entrar-como-orgao`,
        { method: "POST" },
      );
      sessionStorage.setItem("horizon_access", tokens.access_token);
      sessionStorage.setItem("horizon_refresh", tokens.refresh_token);
      sessionStorage.setItem("horizon_painel", tokens.painel);
      window.location.assign("/app/inicio");
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha ao entrar como órgão.");
    } finally {
      setOcupado(false);
    }
  }

  async function previaExclusao(id: string) {
    try {
      const dados = await api<{ usuarios_sinteticos: number; pesquisas: number }>(
        `/lab/cenarios/${id}/exclusao-previa`,
      );
      setPrevia(
        `Seriam removidos ${dados.usuarios_sinteticos} sintéticos e ${dados.pesquisas} pesquisas. Nada foi apagado.`,
      );
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha no dry-run.");
    }
  }

  async function excluir(item: Cenario) {
    if ((confirmar[item.id] || "").trim() !== item.nome) {
      setErro("Digite o nome do cenário para excluir.");
      return;
    }
    setOcupado(true);
    try {
      await api(`/lab/cenarios/${item.id}?confirmo=${encodeURIComponent(item.nome)}`, {
        method: "DELETE",
      });
      await carregar();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Falha ao excluir.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <AppShell>
    <main style={{ padding: 24, maxWidth: 720 }}>
      <p
        style={{
          background: "var(--hz-ink)",
          color: "var(--hz-surface)",
          padding: "8px 12px",
          marginBottom: 16,
        }}
      >
        AMBIENTE DE TESTE — dados sintéticos
      </p>
      <h1>Laboratório</h1>
      <p>
        <Link to="/inicio">Voltar ao início</Link>
      </p>
      {erro ? <p style={{ color: "var(--hz-danger)" }}>{erro}</p> : null}
      {previa ? <p style={{ color: "var(--hz-ok)" }}>{previa}</p> : null}
      <p className="text-[12px] text-[var(--hz-text-2)] mb-3">
        Até 100 pessoas nesta base. 250, 500 e 600 exigem STAGING_DATABASE_URL isolada.
        {limites ? ` Teto do ambiente: ${limites.max_participantes}.` : ""}
      </p>
      <nav style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {[
          ["visao", "Visão"],
          ["orgaos", "Organizações"],
          ["gerador", "Gerador"],
          ["importacao", "Importação"],
          ["editor", "Editor"],
          ["simulador", "Simulador"],
          ["perfis", "Perfis"],
          ["relatorios", "Relatórios"],
          ["limites", "Limites"],
          ["historico", "Histórico"],
        ].map(([id, rotulo]) => (
          <button key={id} type="button" onClick={() => setArea(id)}>
            {rotulo}
          </button>
        ))}
      </nav>

      {(area === "visao" || area === "orgaos" || area === "gerador") && (
      <form onSubmit={criar} style={{ display: "grid", gap: 8, marginBottom: 24 }}>
        <label>
          Nome
          <input value={nome} onChange={(e) => setNome(e.target.value)} required />
        </label>
        <label>
          Tipo
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="CLIMA">CLIMA</option>
            <option value="DESEMPENHO">DESEMPENHO</option>
          </select>
        </label>
        <label>
          Tamanho
          <select
            value={tamanho}
            onChange={(e) => setTamanho(Number(e.target.value))}
          >
            {[10, 25, 50, 100, 250, 500, 600].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label>
          Perfil
          <select value={perfil} onChange={(e) => setPerfil(e.target.value)}>
            {["ALEATORIO", "POSITIVO", "NEUTRO", "NEGATIVO"].map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={ocupado}>
          Criar
        </button>
      </form>
      )}
      {area === "importacao" ? (
        <p>A importação usa a mesma prévia do trabalho. Abra o cenário e a aba Participantes.</p>
      ) : null}
      {area === "editor" ? (
        <p>O editor é o da pesquisa real, aberto a partir do trabalho do cenário.</p>
      ) : null}
      {area === "limites" ? (
        <p>Teto: {limites?.max_participantes ?? "…"}. Acima de 100, a base isolada é obrigatória.</p>
      ) : null}

      <ul style={{ listStyle: "none", padding: 0 }}>
        {lista.map((item) => (
          <li
            key={item.id}
            style={{
              borderTop: "1px solid var(--hz-line)",
              padding: "12px 0",
            }}
          >
            <strong>{item.nome}</strong> — {item.status} ({item.progresso}%)
            {item.erro ? <span> — {item.erro}</span> : null}
            <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                disabled={ocupado || item.status !== "PRONTO"}
                onClick={() => void respostas(item.id)}
              >
                Gerar respostas
              </button>
              {item.projeto_id ? (
                <Link to={`/projetos/${item.projeto_id}?aba=resultados`}>
                  Ver resultado
                </Link>
              ) : null}
              <button
                type="button"
                disabled={ocupado || item.status !== "PRONTO"}
                onClick={() => void entrarOrgao(item.id)}
              >
                Testar como órgão
              </button>
              <button
                type="button"
                disabled={ocupado}
                onClick={() => void previaExclusao(item.id)}
              >
                Dry-run da limpeza
              </button>
              <input
                placeholder="Digite o nome para excluir"
                value={confirmar[item.id] || ""}
                onChange={(e) =>
                  setConfirmar((prev) => ({ ...prev, [item.id]: e.target.value }))
                }
              />
              <button
                type="button"
                disabled={ocupado}
                onClick={() => void excluir(item)}
              >
                Excluir
              </button>
            </div>
            {area === "perfis" && item.status === "PRONTO" ? (
              <form onSubmit={(ev) => void convidar(item.id, ev)} style={{ display: "grid", gap: 8, marginTop: 8 }}>
                <label>
                  Modo
                  <select value={conviteModo} onChange={(e) => setConviteModo(e.target.value)}>
                    <option value="SIMULADO">Simulado (sem e-mail real)</option>
                    <option value="REAL">Real, com consentimento</option>
                  </select>
                </label>
                <input name="nome_convite" placeholder="Nome" required />
                <input name="email_convite" placeholder="E-mail" required />
                <button type="submit" disabled={ocupado}>Enviar convite</button>
              </form>
            ) : null}
            {(item.status === "CRIANDO" || item.status === "EXCLUINDO") && (
              <progress value={item.progresso} max={100} style={{ width: "100%" }} />
            )}
          </li>
        ))}
      </ul>
    </main>
    </AppShell>
  );
}
