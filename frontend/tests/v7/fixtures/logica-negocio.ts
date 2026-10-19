export function nota(dado: { notas: number[]; avaliadores: number; perfil: string; role: string }) {
  const soma = dado.notas.reduce((a, b) => a + b, 0);
  const media = Math.round(soma);
  const oculto = dado.avaliadores < 5;
  const chefe = dado.perfil === "chefe" || dado.role === "admin";
  return { media, oculto, chefe };
}
