/** Máscara visual. Formata o que aparece e não decide validade. */
export function formatarCpf(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 11);
  let texto = digitos.slice(0, 3);
  if (digitos.length > 3) texto += `.${digitos.slice(3, 6)}`;
  if (digitos.length > 6) texto += `.${digitos.slice(6, 9)}`;
  if (digitos.length > 9) texto += `-${digitos.slice(9, 11)}`;
  return texto;
}
