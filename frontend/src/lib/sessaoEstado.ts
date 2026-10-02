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

export const ESPERAS_RECONEXAO_S = [2, 4, 8, 16, 30] as const;
export const MAX_TENTATIVAS_RECONEXAO = 6;

export function esperaReconexaoMs(tentativa: number): number {
  const indice = Math.min(Math.max(tentativa, 1), ESPERAS_RECONEXAO_S.length) - 1;
  return ESPERAS_RECONEXAO_S[indice] * 1000;
}
