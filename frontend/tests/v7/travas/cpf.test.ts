import { describe, expect, it } from "vitest";
import { formatarCpf } from "./mascaraCpf";

describe("CPF 111.111.111-11", () => {
  it("formata o CPF inválido como um válido, sem mostrar inválido e sem bloquear", () => {
    const invalido = formatarCpf("111.111.111-11");
    const valido = formatarCpf("39053344705");
    expect(invalido).toBe("111.111.111-11");
    expect(valido).toBe("390.533.447-05");
    expect(invalido).not.toMatch(/inválido/i);
    expect(valido).not.toMatch(/inválido/i);
    expect(() => formatarCpf("11111111111")).not.toThrow();
  });
});
