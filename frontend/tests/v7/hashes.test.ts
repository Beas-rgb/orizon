import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { raizFront } from "./ajuda";

describe("conferência de hashes", () => {
  it("falha com mensagem clara sem a pasta e sem acessar a rede", () => {
    const script = path.join(raizFront, "tests/v7/conferir-hashes.mjs");
    const fonte = readFileSync(script, "utf8");
    expect(fonte).not.toMatch(/\bfetch\s*\(/);
    let stderr = "";
    try {
      execFileSync(process.execPath, [script], {
        encoding: "utf8",
        env: {
          PATH: process.env.PATH,
          SystemRoot: process.env.SystemRoot,
          COMSPEC: process.env.COMSPEC,
          PATHEXT: process.env.PATHEXT,
        },
      });
    } catch (erro) {
      stderr = String((erro as { stderr?: string }).stderr ?? "");
    }
    expect(stderr).toMatch(/HZ_REFERENCIAS_DIR/);
    expect(stderr).toMatch(/não acessa a rede/);
  });
});
