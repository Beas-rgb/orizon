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

function ProjetoOrgao({ projetoId, onVoltar }) {
  const [aba, setAba] = useState("resultado");
  const [projeto, setProjeto] = useState(null);
  const [pesquisas, setPesquisas] = useState([]);
  const [painel, setPainel] = useState([]);
  const [docs, setDocs] = useState([]);
  const [setores, setSetores] = useState([]);
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    api(`/projetos/${projetoId}`).then(setProjeto).catch((exc) => setAviso(exc.message));
    api(`/projetos/${projetoId}/pesquisas`).then(setPesquisas).catch((exc) => setAviso(exc.message));
    api(`/biblioteca?projeto_id=${projetoId}`).then(setDocs).catch(() => setDocs([]));
    api(`/projetos/${projetoId}/setores`).then(setSetores).catch(() => setSetores([]));
  }, [projetoId]);

  async function verPainel(id) {
    setAviso("");
    try {
      setPainel(await api(`/pesquisas/${id}/painel`));
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  return (
    <div className="grade">
      <aside className="coluna">
        <section className="cartao">
          <h2>Projeto</h2>
          <p className="sub">{projeto ? nomeOrgao(projeto) : "Carregando"}</p>
          <button className="link" type="button" onClick={onVoltar}>Voltar</button>
        </section>
      </aside>
      <main className="principal">
        <section className="cartao">
          <div className="abas" role="tablist">
            {[
              ["resultado", "Resultado"],
              ["dados", "Dados"],
              ["documentos", "Documentos"],
            ].map(([id, rotulo]) => (
              <button key={id} type="button" aria-selected={aba === id} onClick={() => setAba(id)}>
                {rotulo}
              </button>
            ))}
          </div>
          {aviso ? <p className="aviso">{aviso}</p> : null}

          {aba === "resultado" ? (
            <div>
              <h2>Resultado</h2>
              <p className="sub">Só o consolidado. Sem nome e sem nota individual.</p>
              <ul className="lista">
                {pesquisas.map((item) => (
                  <li key={item.id}>
                    <strong>{item.titulo}</strong>
                    <span className="sub">{item.tipo} · {item.status}</span>
                    <button className="link" type="button" onClick={() => verPainel(item.id)}>Ver resultado</button>
                  </li>
                ))}
              </ul>
              {painel.map((item) => (
                <p key={item.pergunta_id} className="sub">
                  {item.texto} · {item.respostas} respostas
                  {item.media != null ? ` · média ${item.media}` : ""}
                </p>
              ))}
            </div>
          ) : null}

          {aba === "dados" && projeto ? (
            <div>
              <h2>Dados do projeto</h2>
              <p>{nomeOrgao(projeto)}</p>
              <p className="sub">{projeto.rotulo} · {projeto.estado} · {projeto.vinculo_titulo}</p>
              <p className="sub">Setores: {setores.map((item) => item.nome).join(", ") || "nenhum"}</p>
            </div>
          ) : null}

          {aba === "documentos" ? (
            <div>
              <h2>Documentos</h2>
              <ul className="lista">
                {docs.length === 0 ? <li className="sub">Nenhum arquivo visível para o órgão.</li> : null}
                {docs.map((item) => (
                  <li key={item.id}>
                    {item.nome}
                    <button className="link" type="button" onClick={() => baixar(item.id, item.nome).catch((exc) => setAviso(exc.message))}>Baixar</button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}

export default function Orgao({ onSair }) {
  const [nome, setNome] = useState("");
  const [projetos, setProjetos] = useState([]);
  const [avisos, setAvisos] = useState([]);
  const [projetoId, setProjetoId] = useState("");
  const [erro, setErro] = useState("");

  useEffect(() => {
    api("/auth/eu").then((eu) => setNome(eu.nome));
    api("/projetos").then(setProjetos).catch((exc) => setErro(exc.message));
    api("/notificacoes").then(setAvisos).catch(() => setAvisos([]));
  }, []);

  async function marcar(id) {
    const atual = await api(`/notificacoes/${id}/lida`, { method: "POST" });
    setAvisos((lista) => lista.map((item) => (item.id === id ? atual : item)));
  }

  return (
    <>
      <header className="topo">
        <div className="marca">
          <span className="selo">OR</span>
          <div>Orizon<small>Órgão</small></div>
        </div>
        <p className="conta">
          <span>{nome}</span>
          <button className="link" type="button" onClick={onSair}>Sair</button>
        </p>
      </header>
      {projetoId ? (
        <ProjetoOrgao projetoId={projetoId} onVoltar={() => setProjetoId("")} />
      ) : (
        <div className="grade">
          <aside className="coluna">
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
            <section className="cartao">
              <h2>Projetos do órgão</h2>
              <p className="sub">Só os projetos em que este órgão participa. Sem edição e sem nota individual.</p>
              {erro ? <p className="erro">{erro}</p> : null}
              <ul className="lista">
                {projetos.map((item) => (
                  <li key={item.id}>
                    <button className="linha" type="button" onClick={() => setProjetoId(item.id)}>
                      <strong>{item.vinculo_titulo || nomeOrgao(item)}</strong>
                      <span className="sub">{item.rotulo} · {item.estado}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          </main>
        </div>
      )}
    </>
  );
}
