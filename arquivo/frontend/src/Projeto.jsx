import { useEffect, useState } from "react";
import { api } from "./api.js";

const TIPOS = [
  ["CLIMA", "Clima"],
  ["DESEMPENHO", "Desempenho"],
  ["CARGOS_SALARIOS", "Cargos e salários"],
  ["PERSONALIZADA", "Personalizada"],
];

const TIPOS_PERGUNTA = [
  ["TEXTO_LIVRE", "Texto livre"],
  ["NOTA_5", "Nota de 1 a 5"],
  ["NOTA_10", "Nota de 1 a 10"],
  ["SIM_NAO", "Sim ou não"],
  ["MULTIPLA_ESCOLHA", "Múltipla escolha"],
  ["CHECKBOX", "Caixas"],
];

export default function Projeto({ projetoId, criando, onCriado, onVoltar }) {
  const [aba, setAba] = useState(criando ? "criar" : "editar");
  const [projeto, setProjeto] = useState(null);
  const [rotulos, setRotulos] = useState([]);
  const [config, setConfig] = useState(null);
  const [setores, setSetores] = useState([]);
  const [pesquisas, setPesquisas] = useState([]);
  const [modelos, setModelos] = useState([]);
  const [docs, setDocs] = useState([]);
  const [entregas, setEntregas] = useState([]);
  const [painel, setPainel] = useState([]);
  const [pesquisaId, setPesquisaId] = useState("");
  const [tokens, setTokens] = useState([]);
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    setAba(criando || !projetoId ? "criar" : "editar");
  }, [criando, projetoId]);

  useEffect(() => {
    api("/projetos/rotulos").then(setRotulos).catch((exc) => setAviso(exc.message));
    api("/modelos").then(setModelos).catch(() => setModelos([]));
  }, []);

  async function recarregar(id) {
    const atual = await api(`/projetos/${id}`);
    const cfg = await api(`/projetos/${id}/configuracao`);
    const listaSetores = await api(`/projetos/${id}/setores`);
    const listaPesquisas = await api(`/projetos/${id}/pesquisas`);
    const listaDocs = await api(`/biblioteca?projeto_id=${id}`);
    const listaEntregas = await api(`/projetos/${id}/entregas`);
    setProjeto(atual);
    setConfig(cfg);
    setSetores(listaSetores);
    setPesquisas(listaPesquisas);
    setDocs(listaDocs);
    setEntregas(listaEntregas);
  }

  useEffect(() => {
    if (!projetoId) return;
    recarregar(projetoId).catch((exc) => setAviso(exc.message));
  }, [projetoId]);

  async function criar(evento) {
    evento.preventDefault();
    setAviso("");
    const form = evento.currentTarget;
    try {
      const criado = await api("/projetos", {
        method: "POST",
        json: {
          rotulo_id: form.rotulo_id.value,
          cnpj: form.cnpj.value,
          email_orgao: form.email_orgao.value,
          vinculo_tipo: form.vinculo_tipo.value,
          vinculo_titulo: form.vinculo_titulo.value,
        },
      });
      onCriado(criado.id);
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function editar(evento) {
    evento.preventDefault();
    setAviso("");
    const form = evento.currentTarget;
    try {
      const atual = await api(`/projetos/${projetoId}`, {
        method: "PATCH",
        json: { estado: form.estado.value, vinculo_titulo: form.vinculo_titulo.value },
      });
      setProjeto(atual);
      setAviso("Edição salva.");
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function salvarFerramentas(evento) {
    evento.preventDefault();
    setAviso("");
    try {
      const atual = await api(`/projetos/${projetoId}/configuracao`, {
        method: "PATCH",
        json: { pesquisas_habilitadas: evento.currentTarget.pesquisas.checked },
      });
      setConfig(atual);
      setAviso("Ferramentas salvas. A IA continua desabilitada.");
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function reenviar() {
    setAviso("");
    try {
      const resposta = await api(`/projetos/${projetoId}/reenviar-convite`, { method: "POST" });
      setAviso(resposta.mensagem);
      await recarregar(projetoId);
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function criarSetor(evento) {
    evento.preventDefault();
    const form = evento.currentTarget;
    try {
      await api(`/projetos/${projetoId}/setores`, {
        method: "POST",
        json: { nome: form.nome.value },
      });
      form.reset();
      setSetores(await api(`/projetos/${projetoId}/setores`));
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function apagarSetor(id) {
    await api(`/projetos/${projetoId}/setores/${id}`, { method: "DELETE" });
    setSetores(await api(`/projetos/${projetoId}/setores`));
  }

  async function criarPesquisa(evento) {
    evento.preventDefault();
    const form = evento.currentTarget;
    try {
      const criada = await api(`/projetos/${projetoId}/pesquisas`, {
        method: "POST",
        json: {
          titulo: form.titulo.value,
          tipo: form.tipo.value,
          descricao: form.descricao.value || null,
        },
      });
      setPesquisaId(criada.id);
      setPesquisas(await api(`/projetos/${projetoId}/pesquisas`));
      setAviso("Pesquisa criada em rascunho.");
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function deModelo(evento) {
    evento.preventDefault();
    const form = evento.currentTarget;
    try {
      const criada = await api(`/projetos/${projetoId}/pesquisas/de-modelo`, {
        method: "POST",
        json: { template_id: form.template_id.value, titulo: form.titulo.value || null },
      });
      setPesquisaId(criada.id);
      setPesquisas(await api(`/projetos/${projetoId}/pesquisas`));
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function pergunta(evento) {
    evento.preventDefault();
    const form = evento.currentTarget;
    const opcoes = form.opcoes.value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((texto) => ({ texto }));
    try {
      await api(`/pesquisas/${pesquisaId}/perguntas`, {
        method: "POST",
        json: {
          texto: form.texto.value,
          tipo: form.tipo.value,
          obrigatoria: form.obrigatoria.checked,
          opcoes,
        },
      });
      form.reset();
      setAviso("Pergunta adicionada.");
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function acaoPesquisa(caminho, depois) {
    setAviso("");
    try {
      const atual = await api(caminho, { method: "POST" });
      if (depois) depois(atual);
      setPesquisas(await api(`/projetos/${projetoId}/pesquisas`));
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  async function verPainel(id) {
    setPesquisaId(id);
    setPainel(await api(`/pesquisas/${id}/painel`));
  }

  async function enviarArquivo(evento) {
    evento.preventDefault();
    const form = evento.currentTarget;
    const dados = new FormData();
    dados.append("arquivo", form.arquivo.files[0]);
    dados.append("projeto_id", projetoId);
    dados.append("camada", form.camada.value);
    if (form.camada.value === "INTERNA") dados.append("visibilidade", form.visibilidade.value);
    try {
      await api("/biblioteca", { method: "POST", body: dados });
      setDocs(await api(`/biblioteca?projeto_id=${projetoId}`));
      setAviso("Arquivo enviado.");
    } catch (exc) {
      setAviso(exc.message);
    }
  }

  return (
    <div className="grade">
      <aside className="coluna">
        <section className="cartao">
          <h2>Projeto</h2>
          <p className="sub">{projeto ? projeto.vinculo_titulo : "Novo projeto"}</p>
          <button className="link" type="button" onClick={onVoltar}>Voltar aos trabalhos</button>
        </section>
      </aside>
      <main className="principal">
        <section className="cartao">
          <div className="abas" role="tablist">
            {[
              ["criar", "Criar"],
              ["editar", "Editar"],
              ["ferramentas", "Ferramentas"],
              ["setores", "Setores"],
              ["pesquisas", "Pesquisas"],
              ["biblioteca", "Biblioteca"],
              ["entregas", "Entregas"],
            ].map(([id, rotulo]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={aba === id}
                disabled={id !== "criar" && !projetoId}
                onClick={() => setAba(id)}
              >
                {rotulo}
              </button>
            ))}
          </div>
          {aviso ? <p className="aviso">{aviso}</p> : null}

          {aba === "criar" ? (
            <form className="formulario" onSubmit={criar}>
              <h2>Criar projeto</h2>
              <label>Rótulo
                <select name="rotulo_id" required>
                  {rotulos.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
                </select>
              </label>
              <label>CNPJ<input name="cnpj" required /></label>
              <label>E-mail do órgão<input name="email_orgao" type="email" required /></label>
              <fieldset className="escolha">
                <legend>Vínculo</legend>
                <label><input type="radio" name="vinculo_tipo" value="EDITAL" defaultChecked /> Edital</label>
                <label><input type="radio" name="vinculo_tipo" value="DOCUMENTO" /> Documento</label>
              </fieldset>
              <label>Título do vínculo<input name="vinculo_titulo" minLength={2} required /></label>
              <button className="acao" type="submit">Criar projeto</button>
            </form>
          ) : null}

          {aba === "editar" && projeto ? (
            <form className="formulario" onSubmit={editar}>
              <h2>Editar projeto</h2>
              <p className="sub">{projeto.razao_social} · {projeto.email_orgao}</p>
              <label>Título do vínculo
                <input name="vinculo_titulo" defaultValue={projeto.vinculo_titulo} required />
              </label>
              <label>Estado
                <select name="estado" defaultValue={projeto.estado}>
                  <option value="ABERTO">Aberto</option>
                  <option value="EM_ANDAMENTO">Em andamento</option>
                  <option value="ENCERRADO">Encerrado</option>
                  <option value="ARQUIVADO">Arquivado</option>
                </select>
              </label>
              <button className="acao" type="submit">Salvar edição</button>
              <button className="acao secundaria" type="button" onClick={reenviar}>Reenviar convite</button>
            </form>
          ) : null}

          {aba === "ferramentas" && config ? (
            <form onSubmit={salvarFerramentas}>
              <h2>Ferramentas</h2>
              <label className="ferramenta">
                <input name="pesquisas" type="checkbox" defaultChecked={config.pesquisas_habilitadas} />
                <span><strong>Pesquisas</strong><span>Desmarque para desabilitar neste projeto.</span></span>
              </label>
              <label className="ferramenta travada">
                <input type="checkbox" checked={false} disabled readOnly />
                <span><strong>IA</strong><span>Desabilitada. A caixa não aceita clique.</span></span>
              </label>
              <button className="acao" type="submit">Salvar ferramentas</button>
            </form>
          ) : null}

          {aba === "setores" && projetoId ? (
            <div>
              <h2>Setores</h2>
              <ul className="lista">
                {setores.map((item) => (
                  <li key={item.id}>
                    {item.nome}
                    <button className="link" type="button" onClick={() => apagarSetor(item.id)}>Remover</button>
                  </li>
                ))}
              </ul>
              <form className="formulario" onSubmit={criarSetor}>
                <label>Nome<input name="nome" minLength={2} required /></label>
                <button className="acao" type="submit">Adicionar setor</button>
              </form>
            </div>
          ) : null}

          {aba === "pesquisas" && projetoId ? (
            <div>
              <h2>Pesquisas</h2>
              <ul className="lista">
                {pesquisas.map((item) => (
                  <li key={item.id}>
                    <strong>{item.titulo}</strong>
                    <span className="sub">{item.tipo} · {item.status}</span>
                    <button className="link" type="button" onClick={() => setPesquisaId(item.id)}>Usar esta</button>
                    <button className="link" type="button" onClick={() => acaoPesquisa(`/pesquisas/${item.id}/publicar`)}>Publicar</button>
                    <button className="link" type="button" onClick={() => acaoPesquisa(`/pesquisas/${item.id}/encerrar`)}>Encerrar</button>
                    <button className="link" type="button" onClick={() => acaoPesquisa(`/pesquisas/${item.id}/tokens?quantidade=1`, (dados) => setTokens(dados.tokens || []))}>Gerar link</button>
                    <button className="link" type="button" onClick={() => verPainel(item.id)}>Painel</button>
                  </li>
                ))}
              </ul>
              <form className="formulario" onSubmit={criarPesquisa}>
                <label>Título<input name="titulo" required /></label>
                <label>Tipo
                  <select name="tipo">{TIPOS.map(([valor, rotulo]) => <option key={valor} value={valor}>{rotulo}</option>)}</select>
                </label>
                <label>Descrição<input name="descricao" /></label>
                <button className="acao" type="submit">Criar pesquisa</button>
              </form>
              <form className="formulario" onSubmit={deModelo}>
                <label>Modelo
                  <select name="template_id" required>
                    {modelos.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
                  </select>
                </label>
                <label>Título no projeto<input name="titulo" /></label>
                <button className="acao secundaria" type="submit">Abrir do modelo</button>
              </form>
              {pesquisaId ? (
                <form className="formulario" onSubmit={pergunta}>
                  <p className="sub">Pergunta na pesquisa selecionada.</p>
                  <label>Texto<textarea name="texto" required /></label>
                  <label>Tipo
                    <select name="tipo">{TIPOS_PERGUNTA.map(([valor, rotulo]) => <option key={valor} value={valor}>{rotulo}</option>)}</select>
                  </label>
                  <label className="ferramenta">
                    <input name="obrigatoria" type="checkbox" defaultChecked />
                    <span>Obrigatória</span>
                  </label>
                  <label>Opções, uma por linha<input name="opcoes" /></label>
                  <button className="acao" type="submit">Adicionar pergunta</button>
                  <button
                    className="acao secundaria"
                    type="button"
                    onClick={() => {
                      const nome = window.prompt("Nome do modelo");
                      if (!nome) return;
                      api(`/pesquisas/${pesquisaId}/modelo`, { method: "POST", json: { nome } })
                        .then(() => setAviso("Modelo salvo."))
                        .catch((exc) => setAviso(exc.message));
                    }}
                  >
                    Salvar como modelo
                  </button>
                </form>
              ) : null}
              {tokens.length ? <p className="sub">Links: {tokens.join(" ")}</p> : null}
              {painel.length ? (
                <ul className="lista">
                  {painel.map((item) => (
                    <li key={item.pergunta_id}>{item.texto} · {item.respostas} respostas{item.media != null ? ` · média ${item.media}` : ""}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {aba === "biblioteca" && projetoId ? (
            <div>
              <h2>Biblioteca</h2>
              <ul className="lista">
                {docs.map((item) => (
                  <li key={item.id}>{item.nome} · {item.camada} · {item.visibilidade}</li>
                ))}
              </ul>
              <form className="formulario" onSubmit={enviarArquivo}>
                <label>Arquivo<input name="arquivo" type="file" required /></label>
                <label>Camada
                  <select name="camada" defaultValue="EXTERNA">
                    <option value="EXTERNA">Externa, só a consultora</option>
                    <option value="INTERNA">Interna do projeto</option>
                  </select>
                </label>
                <label>Quem vê, se interna
                  <select name="visibilidade" defaultValue="PRIVADO">
                    <option value="PRIVADO">Só a consultora</option>
                    <option value="ORGAO">Órgão</option>
                    <option value="FUNCIONARIOS">Funcionários</option>
                    <option value="PUBLICO_PROJETO">Todos do projeto</option>
                  </select>
                </label>
                <button className="acao" type="submit">Enviar arquivo</button>
              </form>
            </div>
          ) : null}

          {aba === "entregas" && projetoId ? (
            <div>
              <h2>Entregas</h2>
              <ul className="lista">
                {entregas.map((item) => (
                  <li key={item.id}>{item.destino} · {item.assunto} · {item.status}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}
