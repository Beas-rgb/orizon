import { useEffect, useState } from "react";
import { api, guardarSessao, limparSessao, painelAtual, sair, tokenAtual } from "./api.js";
import Dev from "./Dev.jsx";
import Funcionario from "./Funcionario.jsx";
import Orgao from "./Orgao.jsx";
import Projeto from "./Projeto.jsx";
import { InicioPublico, PrimeiroAcesso } from "./Publico.jsx";

const ENCERRADOS = new Set(["ENCERRADO", "ARQUIVADO"]);

function nomeOrgao(item) {
  return item.nome_fantasia || item.razao_social;
}

function Cabeca({ nome, papel, onInicio, onSair }) {
  const rotulo = papel === "orgao" ? "Órgão" : "Consultora";
  return (
    <header className="topo">
      <button className="marca" type="button" onClick={onInicio}>
        <span className="selo">OR</span>
        <div>Orizon<small>{rotulo}</small></div>
      </button>
      <p className="conta">
        <span>{nome}</span>
        <button className="link" type="button" onClick={onSair}>Sair</button>
      </p>
    </header>
  );
}

function Login({ onEntrou, onVoltar }) {
  const [erro, setErro] = useState("");

  async function enviar(evento) {
    evento.preventDefault();
    setErro("");
    const form = evento.currentTarget;
    try {
      const dados = await api("/auth/login", {
        method: "POST",
        json: { email: form.email.value, senha: form.senha.value },
      });
      if (!["consultora", "orgao", "funcionario", "dev"].includes(dados.painel)) {
        setErro("Este acesso não abre painel.");
        return;
      }
      guardarSessao(dados);
      onEntrou();
    } catch (exc) {
      setErro(exc.message);
    }
  }

  return (
    <main className="login-pagina">
      <form className="login" onSubmit={enviar}>
        <div className="marca">
          <span className="selo">OR</span>
          <div>Orizon<small>Consultora</small></div>
        </div>
        <p className="sub">A tela abre conforme a conta: consultora, órgão ou funcionário.</p>
        <label>E-mail<input name="email" type="email" required /></label>
        <label>Senha<input name="senha" type="password" required /></label>
        {erro ? <p className="erro">{erro}</p> : null}
        <button className="acao" type="submit">Entrar</button>
        <button className="link" type="button" onClick={onVoltar}>Voltar</button>
      </form>
    </main>
  );
}

function Convites() {
  const [aviso, setAviso] = useState("");

  async function convidar(papel) {
    setAviso("");
    const nome = window.prompt(papel === "ORGAO" ? "Nome do órgão" : "Nome do desenvolvimento");
    const email = window.prompt("E-mail do convite");
    if (!nome || !email) return;
    try {
      const resposta = await api("/auth/convites", {
        method: "POST",
        json: { nome, email, papel },
      });
      setAviso(resposta.mensagem + " O token fica no e-mail local, não nesta tela.");
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  return (
    <section className="cartao">
      <h2>Acessos</h2>
      <p className="sub">O órgão define a própria senha no primeiro acesso. O funcionário só entra depois de um projeto.</p>
      <button className="atalho" type="button" onClick={() => convidar("ORGAO")}>
        <span><strong>Convidar órgão</strong><span>Um acesso por vez</span></span>
      </button>
      <button className="atalho" type="button" onClick={() => convidar("TI")}>
        <span><strong>Convidar desenvolvimento</strong><span>Só informação técnica</span></span>
      </button>
      {aviso ? <p className="aviso">{aviso}</p> : null}
    </section>
  );
}

function Inicio({ onAbrir, onCriar }) {
  const [projetos, setProjetos] = useState([]);
  const [avisos, setAvisos] = useState([]);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api("/projetos").then(setProjetos).catch((exc) => setErro(exc.message));
    api("/notificacoes").then(setAvisos).catch(() => setAvisos([]));
  }, []);

  const abertos = projetos.filter((item) => item.estado === "ABERTO");
  const andamento = projetos.filter((item) => item.estado === "EM_ANDAMENTO");
  const concluidos = projetos.filter((item) => ENCERRADOS.has(item.estado));

  async function marcar(id) {
    const atual = await api(`/notificacoes/${id}/lida`, { method: "POST" });
    setAvisos((lista) => lista.map((item) => (item.id === id ? atual : item)));
  }

  return (
    <div className="grade">
      <aside className="coluna">
        <section className="cartao">
          <h2>Acesso rápido</h2>
          <button className="atalho" type="button" onClick={onCriar}>
            <span><strong>Novo trabalho</strong><span>Criar projeto</span></span>
          </button>
        </section>
        <Convites />
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
          <h2>Métricas de trabalhos</h2>
          <div className="metricas">
            <article className="metrica ini"><span>INI</span><strong>{abertos.length}</strong><span>Iniciados</span></article>
            <article className="metrica and"><span>AND</span><strong>{andamento.length}</strong><span>Em andamento</span></article>
            <article className="metrica con"><span>CON</span><strong>{concluidos.length}</strong><span>Concluídos</span></article>
          </div>
        </section>
        <section className="cartao">
          <h2>Histórico recente</h2>
          {erro ? <p className="erro">{erro}</p> : null}
          <ul className="lista">
            {projetos.map((item) => (
              <li key={item.id}>
                <button className="linha" type="button" onClick={() => onAbrir(item.id)}>
                  <strong>{item.vinculo_titulo || nomeOrgao(item)}</strong>
                  <span className="sub">{nomeOrgao(item)} · {item.rotulo} · {item.estado}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}

export default function App() {
  const [pronto, setPronto] = useState(false);
  const [nome, setNome] = useState("");
  const [papel, setPapel] = useState("");
  const [tela, setTela] = useState("inicio");
  const [porta, setPorta] = useState(() => (window.location.hash.length > 1 ? "acesso" : "inicio"));
  const [projetoId, setProjetoId] = useState("");

  async function carregarConta() {
    const painel = painelAtual();
    if (!tokenAtual() || !["consultora", "orgao", "funcionario", "dev"].includes(painel)) {
      limparSessao();
      setPronto(true);
      return;
    }
    try {
      const eu = await api("/auth/eu");
      if (!["consultora", "orgao", "funcionario", "dev"].includes(eu.painel)) {
        limparSessao();
        setPronto(true);
        return;
      }
      setNome(eu.nome);
      setPapel(eu.painel);
      setPronto(true);
    } catch {
      limparSessao();
      setPronto(true);
    }
  }

  useEffect(() => {
    carregarConta();
  }, []);

  async function encerrar() {
    await sair();
    setNome("");
    setPapel("");
    setTela("inicio");
    setProjetoId("");
  }

  if (!pronto) return null;
  if (!tokenAtual()) {
    if (porta === "login") return <Login onEntrou={carregarConta} onVoltar={() => setPorta("inicio")} />;
    if (porta === "acesso") return <PrimeiroAcesso onEntrou={carregarConta} onVoltar={() => setPorta("inicio")} />;
    return <InicioPublico onLogin={() => setPorta("login")} onAcesso={() => setPorta("acesso")} />;
  }

  return (
    <>
      {papel === "dev" ? <Dev nome={nome} onSair={encerrar} /> : null}
      {papel === "orgao" ? <Orgao onSair={encerrar} /> : null}
      {papel === "funcionario" ? <Funcionario onSair={encerrar} /> : null}
      {papel === "consultora" ? (
      <>
      <Cabeca nome={nome} papel={papel} onInicio={() => { setTela("inicio"); setProjetoId(""); }} onSair={encerrar} />
      {tela === "inicio" ? (
        <Inicio
          onAbrir={(id) => { setProjetoId(id); setTela("projeto"); }}
          onCriar={() => { setProjetoId(""); setTela("criar"); }}
        />
      ) : (
        <Projeto
          projetoId={projetoId}
          criando={tela === "criar"}
          onCriado={(id) => { setProjetoId(id); setTela("projeto"); }}
          onVoltar={() => setTela("inicio")}
        />
      )}
      </>
      ) : null}
    </>
  );
}
