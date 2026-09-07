import { useState } from "react";
import { api, guardarSessao } from "./api.js";

export function InicioPublico({ onLogin, onAcesso }) {
  return (
    <div className="publico">
      <header className="topo">
        <div className="marca">
          <span className="selo">OR</span>
          <div>Orizon<small>Serviço público</small></div>
        </div>
        <p className="conta">
          <button className="acao secundaria" type="button" onClick={onAcesso}>Primeiro acesso</button>
          <button className="acao" type="button" onClick={onLogin}>Entrar</button>
        </p>
      </header>
      <main className="hero-publico">
        <p className="olho">SERVIÇO PÚBLICO</p>
        <h1>A pesquisa do órgão, do pedido à nota.</h1>
        <p className="lead">
          A consultora aplica, o funcionário responde e vê a própria nota, o órgão consulta o resultado.
        </p>
        <button className="acao" type="button" onClick={onLogin}>Entrar</button>
      </main>
    </div>
  );
}

export function PrimeiroAcesso({ onVoltar, onEntrou }) {
  const [erro, setErro] = useState("");
  const [token, setToken] = useState(
    () => decodeURIComponent(window.location.hash.replace(/^#/, "")).trim()
  );

  async function enviar(evento) {
    evento.preventDefault();
    setErro("");
    const form = evento.currentTarget;
    try {
      const dados = await api("/auth/primeiro-acesso", {
        method: "POST",
        json: { token: token.trim(), senha: form.senha.value },
      });
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
          <div>Orizon<small>Primeiro acesso</small></div>
        </div>
        <p className="sub">Cole o token do convite e defina a senha. A senha não chega por e-mail.</p>
        <label>Token
          <input value={token} onChange={(evento) => setToken(evento.target.value)} required />
        </label>
        <label>Senha<input name="senha" type="password" minLength={8} required /></label>
        {erro ? <p className="erro">{erro}</p> : null}
        <button className="acao" type="submit">Definir senha</button>
        <button className="link" type="button" onClick={onVoltar}>Voltar</button>
      </form>
    </main>
  );
}
