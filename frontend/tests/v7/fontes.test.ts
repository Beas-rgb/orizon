import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { raizFront } from "./ajuda";

const ESPERADOS = {
  "Inter.ttf": "0be2399ea925f1f83ff974764761da9860ec50742ed29a5d4c1ffd0c5c7ac3a8",
  "Montserrat.ttf": "498dc34d0fa45288e0ac5345bd385c98bf81c56ee70209aacfb4a22a6510697c",
};

function hashDe(bytes: Buffer) {
  return createHash("sha256").update(bytes).digest("hex");
}

describe("fontes locais", () => {
  it("confere os sha256 e reprova um byte alterado", () => {
    for (const [nome, esperado] of Object.entries(ESPERADOS)) {
      const bytes = readFileSync(path.join(raizFront, "src/assets/fonts", nome));
      expect(hashDe(bytes)).toBe(esperado);
      const alterado = Buffer.from(bytes);
      alterado[0] ^= 0xff;
      expect(hashDe(alterado)).not.toBe(esperado);
    }
  });
});
