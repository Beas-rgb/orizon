import { execFileSync } from "node:child_process";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { raizFront } from "./ajuda";

function rodar(args: string[]) {
  try {
    const stdout = execFileSync(process.execPath, [path.join(raizFront, "scripts/checar_hex.mjs"), ...args], {
      cwd: raizFront,
      encoding: "utf8",
    });
    return { status: 0, stdout, stderr: "" };
  } catch (erro) {
    const falha = erro as { status?: number; stdout?: string; stderr?: string };
    return { status: falha.status ?? 1, stdout: String(falha.stdout ?? ""), stderr: String(falha.stderr ?? "") };
  }
}

describe("checar hex", () => {
  it("sem argumento informa a pasta src", () => {
    const resultado = rodar([]);
    expect(resultado.status).toBe(0);
    expect(resultado.stdout).toMatch(/pasta=src/);
  });

  it("com --raiz deixa o hex dos tokens e reprova o de fora", () => {
    const vazio = rodar(["--raiz"]);
    expect(vazio.status).toBe(2);
    const resultado = rodar(["--raiz", path.join(raizFront, "tests/v7/fixtures/checar-hex")]);
    expect(resultado.status).not.toBe(0);
    expect(resultado.stderr).toContain("src/v7/outra/x.css:2");
    expect(resultado.stderr).not.toContain("src/v7/tokens/ok.css");
  });
});
