import { useEffect, useState } from "react";
import { api } from "./api.js";

export default function Dev({ nome, onSair }) {
  const [saude, setSaude] = useState(null);
  const [banco, setBanco] = useState(null);
  const [email, setEmail] = useState(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api("/health").then(setSaude).catch((exc) => setErro(exc.message));
    api("/health/db").then(setBanco).catch((exc) => setBanco({ status: exc.message }));
    api("/health/email").then(setEmail).catch((exc) => setEmail({ modo: exc.message }));
  }, []);

  return (
    <>
      <header className="topo">
        <div className="marca">
          <span className="selo">OR</span>
          <div>Orizon<small>Desenvolvimento</small></div>
        </div>
        <p className="conta">
          <span>{nome}</span>
          <button className="link" type="button" onClick={onSair}>Sair</button>
        </p>
      </header>
      <div className="grade">
        <main className="principal">
          <section className="cartao">
            <h2>Informação técnica</h2>
            <p className="sub">
              Este acesso não vê projeto, resposta nem arquivo. Só o estado da API.
            </p>
            {erro ? <p className="erro">{erro}</p> : null}
            <ul className="lista">
              <li><strong>API</strong><span className="sub">{saude ? saude.status : "consultando"}</span></li>
              <li><strong>Banco</strong><span className="sub">{banco ? banco.status : "consultando"}</span></li>
              <li><strong>E-mail</strong><span className="sub">{email ? email.modo : "consultando"}</span></li>
            </ul>
            <p className="sub">
              E-mail em modo local grava o convite em data/outbox/ultimo.txt. Não publica senha nem token na tela.
            </p>
          </section>
        </main>
      </div>
    </>
  );
}
