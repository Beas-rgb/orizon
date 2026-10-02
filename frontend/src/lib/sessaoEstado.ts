export class ApiErro extends Error {
  status: number;
  rede: boolean;

  constructor(status: number, mensagem: string, rede = false) {
    super(mensagem);
    this.name = "ApiErro";
    this.status = status;
    this.rede = rede;
  }
}

/** Só o acesso recusado encerra a sessão. Rede e 5xx deixam o token no navegador. */
export function sessaoEncerrada(erro: unknown): boolean {
  return erro instanceof ApiErro && erro.status === 401 && !erro.rede;
}

export function falhaPassageira(erro: unknown): boolean {
  return (
    erro instanceof ApiErro &&
    (erro.rede || erro.status === 0 || erro.status >= 500)
  );
}
