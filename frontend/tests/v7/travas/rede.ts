export type Rota = {
  url: () => string;
  abort: (motivo?: string) => void;
};

export type Pagina = {
  route: (padrao: string, tratar: (rota: Rota) => void) => void;
};

export type AlvoDeRede = {
  fetch: (...args: unknown[]) => unknown;
  XMLHttpRequest: new (...args: unknown[]) => unknown;
  WebSocket: new (...args: unknown[]) => unknown;
  EventSource: new (...args: unknown[]) => unknown;
  navigator: { sendBeacon: (...args: unknown[]) => unknown };
  api?: (...args: unknown[]) => unknown;
};

function proibirRede(): never {
  throw new Error("Rede proibida no front v7.");
}

export function travarRede(alvo: AlvoDeRede) {
  alvo.fetch = proibirRede;
  alvo.XMLHttpRequest = proibirRede as AlvoDeRede["XMLHttpRequest"];
  alvo.WebSocket = proibirRede as AlvoDeRede["WebSocket"];
  alvo.EventSource = proibirRede as AlvoDeRede["EventSource"];
  alvo.navigator.sendBeacon = proibirRede;
  if ("api" in alvo) alvo.api = proibirRede;
}

/** page.route("**\/*") reprova qualquer requisição. */
export function instalarPageRoute(pagina: Pagina) {
  pagina.route("**/*", (rota) => {
    rota.abort("blockedbyclient");
  });
}
