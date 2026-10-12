import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "../components/layout/AppShell";
import { api } from "../lib/api";
import { EstadoMensagem, TelaCarregando, TelaErro, TelaVazia } from "../ui";

type Nota = {
  tipo: string;
  mensagem: string;
  nota: number | null;
  comprovante?: string | null;
  perspectivas_suprimidas?: string[];
};

type Minha = {
  pesquisa_id: string;
  titulo: string;
  tipo: string;
  status_participacao: string;
};

export function MinhaContaPage() {
  const [msg, setMsg] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function salvar(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setErro("");
    setMsg("");
    const form = ev.currentTarget;
    setEnviando(true);
    try {
      const resp = await api<{ mensagem: string }>("/auth/senha", {
        method: "POST",
        json: {
          senha_atual: (form.elements.namedItem("atual") as HTMLInputElement).value,
          senha_nova: (form.elements.namedItem("nova") as HTMLInputElement).value,
        },
      });
      setMsg(resp.mensagem);
      form.reset();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <AppShell>
      <h1 className="mb-1 text-[18px] font-bold text-[var(--hz-ink)]">Minha conta</h1>
      <p className="mb-5 text-[12px] text-[var(--hz-text-2)]">Troque a senha com a senha atual.</p>
      {erro ? <EstadoMensagem tom="erro">{erro}</EstadoMensagem> : null}
      {msg ? <EstadoMensagem tom="ok">{msg}</EstadoMensagem> : null}
      <form onSubmit={salvar} className="grid max-w-md gap-3">
        <label className="text-[12px] font-semibold">
          Senha atual
          <input name="atual" type="password" required className="mt-1 w-full rounded-xl px-3 py-2.5" />
        </label>
        <label className="text-[12px] font-semibold">
          Nova senha
          <input name="nova" type="password" required minLength={8} className="mt-1 w-full rounded-xl px-3 py-2.5" />
        </label>
        <button
          type="submit"
          disabled={enviando}
          className="rounded-xl py-2.5 text-[13px] font-bold text-[var(--hz-surface)]"
          style={{ background: "var(--hz-ink)" }}
        >
          {enviando ? "Salvando…" : "Atualizar senha"}
        </button>
      </form>
    </AppShell>
  );
}

export function MinhasNotasPage() {
  const [itens, setItens] = useState<Minha[] | null>(null);
  const [nota, setNota] = useState<Nota | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Minha[]>("/eu/pesquisas")
      .then(setItens)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  async function abrir(id: string) {
    setErro("");
    try {
      setNota(await api<Nota>(`/eu/pesquisas/${id}/nota`));
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : "Erro");
    }
  }

  const concluidas = (itens || []).filter((i) => i.status_participacao === "RESPONDIDA");

  return (
    <AppShell>
      <h1 className="mb-1 text-[18px] font-bold text-[var(--hz-ink)]">Minhas notas</h1>
      <p className="mb-5 text-[12px] text-[var(--hz-text-2)]">
        A nota dos subordinados some quando menos de 5 pessoas responderam.
      </p>
      {erro ? <TelaErro texto={erro} /> : null}
      {itens === null && !erro ? <TelaCarregando /> : null}
      {itens && concluidas.length === 0 ? (
        <TelaVazia titulo="Nenhuma nota ainda" texto="Quando você responder, a nota aparece aqui." />
      ) : null}
      <ul className="flex flex-col gap-2">
        {concluidas.map((item) => (
          <li key={item.pesquisa_id}>
            <button
              type="button"
              className="w-full rounded-2xl bg-[var(--hz-surface)] p-3 text-left"
              onClick={() => void abrir(item.pesquisa_id)}
            >
              <p className="text-[14px] font-semibold">{item.titulo}</p>
              <p className="text-[12px] text-[var(--hz-text-2)]">{item.tipo}</p>
            </button>
          </li>
        ))}
      </ul>
      {nota ? (
        <div className="mt-4 rounded-3xl bg-[var(--hz-surface)] p-4">
          <p className="text-[13px]">{nota.mensagem}</p>
          {nota.nota != null ? (
            <p className="mt-2 text-[24px] font-bold">{nota.nota.toFixed(1)}</p>
          ) : (
            <EstadoMensagem tom="aviso">Nota omitida para preservar o anonimato.</EstadoMensagem>
          )}
        </div>
      ) : null}
    </AppShell>
  );
}

type Aviso = { id: string; titulo: string; lida: boolean; corpo?: string };

export function NotificacoesPage() {
  const [itens, setItens] = useState<Aviso[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Aviso[]>("/notificacoes")
      .then(setItens)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  async function marcar(id: string) {
    await api(`/notificacoes/${id}/lida`, { method: "POST" });
    setItens((atual) =>
      (atual || []).map((item) => (item.id === id ? { ...item, lida: true } : item)),
    );
  }

  return (
    <AppShell>
      <h1 className="mb-4 text-[18px] font-bold text-[var(--hz-ink)]">Notificações</h1>
      {erro ? <TelaErro texto={erro} /> : null}
      {itens === null && !erro ? <TelaCarregando /> : null}
      {itens && itens.length === 0 ? <TelaVazia titulo="Nenhuma notificação" /> : null}
      <ul className="flex flex-col gap-2">
        {(itens || []).map((item) => (
          <li key={item.id} className="rounded-2xl bg-[var(--hz-surface)] p-3">
            <p className="text-[14px] font-semibold">{item.titulo}</p>
            {!item.lida ? (
              <button
                type="button"
                className="mt-2 text-[12px] font-bold text-[var(--hz-accent)]"
                onClick={() => void marcar(item.id)}
              >
                Marcar como lida
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </AppShell>
  );
}

type Doc = { id: string; nome: string; visibilidade: string; tamanho: number };

export function DocumentosPage() {
  const [itens, setItens] = useState<Doc[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Doc[]>("/biblioteca")
      .then(setItens)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  return (
    <AppShell>
      <h1 className="mb-4 text-[18px] font-bold text-[var(--hz-ink)]">Documentos</h1>
      {erro ? <TelaErro texto={erro} /> : null}
      {itens === null && !erro ? <TelaCarregando /> : null}
      {itens && itens.length === 0 ? (
        <TelaVazia titulo="Nenhum documento compartilhado" />
      ) : null}
      <ul className="flex flex-col gap-2">
        {(itens || []).map((doc) => (
          <li key={doc.id} className="rounded-2xl bg-[var(--hz-surface)] p-3">
            <p className="text-[14px] font-semibold">{doc.nome}</p>
            <p className="text-[12px] text-[var(--hz-text-2)]">{doc.visibilidade}</p>
            <a
              className="text-[12px] font-bold text-[var(--hz-accent)]"
              href={`/biblioteca/${doc.id}/arquivo`}
            >
              Baixar
            </a>
          </li>
        ))}
      </ul>
    </AppShell>
  );
}

type Modelo = { id: string; nome: string; tipo: string };

export function BancoPerguntasPage() {
  const [itens, setItens] = useState<Modelo[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Modelo[]>("/modelos")
      .then(setItens)
      .catch((exc) => setErro(exc instanceof Error ? exc.message : "Erro"));
  }, []);

  return (
    <AppShell>
      <h1 className="mb-4 text-[18px] font-bold text-[var(--hz-ink)]">Banco de perguntas</h1>
      {erro ? <TelaErro texto={erro} /> : null}
      {itens === null && !erro ? <TelaCarregando /> : null}
      {itens && itens.length === 0 ? (
        <TelaVazia titulo="Nenhum modelo" texto="Salve uma pesquisa como modelo para reutilizar as perguntas." />
      ) : null}
      <ul className="flex flex-col gap-2">
        {(itens || []).map((m) => (
          <li key={m.id} className="rounded-2xl bg-[var(--hz-surface)] p-3">
            <p className="text-[14px] font-semibold">{m.nome}</p>
            <p className="text-[12px] text-[var(--hz-text-2)]">{m.tipo}</p>
          </li>
        ))}
      </ul>
    </AppShell>
  );
}
