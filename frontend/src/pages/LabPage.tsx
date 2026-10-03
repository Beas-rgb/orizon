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

  const carregar = useCallback(async () => {
    try {
      const dados = await api<Cenario[]>("/lab/cenarios");
      setLista(dados);
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
            {[100, 250, 500, 1000, 5000].map((n) => (
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
