export function usuarioVeioNoLogin(dados: { usuario?: { id?: string } | null }) {
  return Boolean(dados.usuario?.id);
}
