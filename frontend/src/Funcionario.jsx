import { useEffect, useState } from "react";
import { api, tokenAtual, urlApi } from "./api.js";

function nomeOrgao(item) {
  return item.nome_fantasia || item.razao_social;
}

async function baixar(id, nome) {
  const resposta = await fetch(urlApi(`/biblioteca/${id}/arquivo`), {
    headers: { Authorization: `Bearer ${tokenAtual()}` },
  });
  if (!resposta.ok) throw new Error("Não foi possível baixar o arquivo.");
  const blob = await resposta.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  link.click();
  URL.revokeObjectURL(url);
}

function Campo({ pergunta, valor, onChange }) {
  if (pergunta.tipo === "TEXTO_LIVRE") {
    return <input value={valor.valor_texto || ""} onChange={(evento) => onChange({ valor_texto: evento.target.value })} />;
  }
  if (pergunta.tipo === "NOTA_5" || pergunta.tipo === "NOTA_10") {
    const maximo = pergunta.tipo === "NOTA_5" ? 5 : 10;
    return (
      <input
        type="number"
        min="1"
        max={maximo}
        value={valor.valor_numerico ?? ""}
        onChange={(evento) => onChange({ valor_numerico: Number(evento.target.value) })}
      />
    );
  }
  if (pergunta.tipo === "SIM_NAO") {
    return (
      <div className="escolha">
        {["sim", "não"].map((texto) => (
          <label key={texto}>
            <input
              type="radio"
              name={pergunta.id}
              checked={valor.valor_texto === texto}
              onChange={() => onChange({ valor_texto: texto })}
            />
            {texto}
          </label>
        ))}
      </div>
    );
  }
  if (pergunta.tipo === "CHECKBOX") {
    const marcadas = new Set(valor.opcoes || []);
    return (
      <div className="escolha">
        {(pergunta.opcoes || []).map((opcao) => (
          <label key={opcao.id}>
            <input
              type="checkbox"
              checked={marcadas.has(opcao.id)}
              onChange={(evento) => {
                const proxima = new Set(marcadas);
                if (evento.target.checked) proxima.add(opcao.id);
                else proxima.delete(opcao.id);
                onChange({ opcoes: [...proxima] });
              }}
            />
            {opcao.texto}
          </label>
        ))}
      </div>
    );
  }
  return (
    <div className="escolha">
      {(pergunta.opcoes || []).map((opcao) => (
        <label key={opcao.id}>
          <input
            type="radio"
            name={pergunta.id}
            checked={valor.opcao_id === opcao.id}
            onChange={() => onChange({ opcao_id: opcao.id })}
          />
          {opcao.texto}
        </label>
      ))}
    </div>
  );
}

function Responder({ tokenInicial }) {
  const [token, setToken] = useState(tokenInicial || "");
  const [perguntas, setPerguntas] = useState([]);
  const [valores, setValores] = useState({});
  const [nota, setNota] = useState(null);
  const [aviso, setAviso] = useState("");

  async function abrir(evento) {
    evento?.preventDefault();
    setAviso("");
    setNota(null);
    try {
      const lista = await api(`/responder/${encodeURIComponent(token.trim())}`);
      setPerguntas(lista);
    } catch (exc) {
      setPerguntas([]);
      setAviso(exc.message);
    }
  }

  async function enviar(evento) {
    evento.preventDefault();
    setAviso("");
    const respostas = [];
    for (const pergunta of perguntas) {
      const valor = valores[pergunta.id] || {};
      if (pergunta.tipo === "CHECKBOX") {
        for (const opcaoId of valor.opcoes || []) {
          respostas.push({ pergunta_id: pergunta.id, opcao_id: opcaoId });
        }
        continue;
      }
      respostas.push({
        pergunta_id: pergunta.id,
        valor_texto: valor.valor_texto || null,
        valor_numerico: valor.valor_numerico ?? null,
        opcao_id: valor.opcao_id || null,
      });
    }
    try {
      setNota(await api(`/responder/${encodeURIComponent(token.trim())}`, {
        method: "POST",
        json: { respostas },
      }));
      setPerguntas([]);
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function verNota() {
    setAviso("");
    try {
      setNota(await api(`/responder/${encodeURIComponent(token.trim())}/nota`));
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  return (
    <section className="cartao">
      <h2>Responder</h2>
      <p className="sub">O link é o acesso. A nota de desempenho volta só para quem tem esse token.</p>
      <form className="formulario" onSubmit={abrir}>
        <label>Token do convite<input value={token} onChange={(evento) => setToken(evento.target.value)} required /></label>
        <button className="acao" type="submit">Abrir pesquisa</button>
        <button className="acao secundaria" type="button" onClick={verNota}>Ver minha nota</button>
      </form>
      {aviso ? <p className="erro">{aviso}</p> : null}
      {nota ? (
        <p>{nota.mensagem}{nota.nota != null ? ` ${nota.nota}` : ""}</p>
      ) : null}
      {perguntas.length ? (
        <form className="formulario" onSubmit={enviar}>
          {perguntas.map((pergunta) => (
            <label key={pergunta.id}>
              {pergunta.texto}
              <Campo
                pergunta={pergunta}
                valor={valores[pergunta.id] || {}}
                onChange={(valor) => setValores((atual) => ({ ...atual, [pergunta.id]: valor }))}
              />
            </label>
          ))}
          <button className="acao" type="submit">Enviar respostas</button>
        </form>
      ) : null}
    </section>
  );
}

export default function Funcionario({ onSair }) {
  const [nome, setNome] = useState("");
  const [aba, setAba] = useState("projetos");
  const [projetos, setProjetos] = useState([]);
  const [docs, setDocs] = useState([]);
  const [avisos, setAvisos] = useState([]);
  const [erro, setErro] = useState("");
  const tokenHash = decodeURIComponent(window.location.hash.replace(/^#/, "")).trim();

  useEffect(() => {
    api("/auth/eu").then((eu) => setNome(eu.nome));
    api("/projetos").then(setProjetos).catch((exc) => setErro(exc.message));
    api("/biblioteca").then(setDocs).catch(() => setDocs([]));
    api("/notificacoes").then(setAvisos).catch(() => setAvisos([]));
    if (tokenHash) setAba("responder");
  }, [tokenHash]);

  async function marcar(id) {
    const atual = await api(`/notificacoes/${id}/lida`, { method: "POST" });
    setAvisos((lista) => lista.map((item) => (item.id === id ? atual : item)));
  }

  return (
    <>
      <header className="topo">
        <div className="marca">
          <span className="selo">OR</span>
          <div>Orizon<small>Funcionário</small></div>
        </div>
        <p className="conta">
          <span>{nome}</span>
          <button className="link" type="button" onClick={onSair}>Sair</button>
        </p>
      </header>
      <div className="grade">
        <aside className="coluna">
          <section className="cartao">
            <h2>Acesso</h2>
            <button className="atalho" type="button" onClick={() => setAba("projetos")}>
              <span><strong>Projetos</strong><span>Onde você participa</span></span>
            </button>
            <button className="atalho" type="button" onClick={() => setAba("documentos")}>
              <span><strong>Documentos</strong><span>O que você pode ver</span></span>
            </button>
            <button className="atalho" type="button" onClick={() => setAba("responder")}>
              <span><strong>Responder</strong><span>Pelo token da pesquisa</span></span>
            </button>
          </section>
          <section className="cartao">
            <h2>Avisos</h2>
            <ul className="lista">
              {avisos.length === 0 ? <li className="sub">Nenhum aviso.</li> : null}
              {avisos.map((item) => (
                <li key={item.id}>
                  <strong>{item.titulo}</strong>
                  <span className="sub">{item.mensagem}</span>
                  {item.lida ? null : (
                    <button className="link" type="button" onClick={() => marcar(item.id)}>Marcar lido</button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </aside>
        <main className="principal">
          {aba === "projetos" ? (
            <section className="cartao">
              <h2>Meus projetos</h2>
              <p className="sub">A lista só mostra projeto em que você está. Não abre o resultado dos outros.</p>
              {erro ? <p className="erro">{erro}</p> : null}
              <ul className="lista">
                {projetos.map((item) => (
                  <li key={item.id}>
                    <strong>{item.vinculo_titulo || nomeOrgao(item)}</strong>
                    <span className="sub">{item.rotulo} · {item.estado}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {aba === "documentos" ? (
            <section className="cartao">
              <h2>Documentos</h2>
              <ul className="lista">
                {docs.length === 0 ? <li className="sub">Nenhum arquivo visível para você.</li> : null}
                {docs.map((item) => (
                  <li key={item.id}>
                    {item.nome}
                    <button className="link" type="button" onClick={() => baixar(item.id, item.nome).catch((exc) => setErro(exc.message))}>Baixar</button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {aba === "responder" ? <Responder tokenInicial={tokenHash} /> : null}
        </main>
      </div>
    </>
  );
}
