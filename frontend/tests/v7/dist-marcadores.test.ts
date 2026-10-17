import { execFileSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { raizFront } from "./ajuda";
import { marcadoresProibidos, procurarMarcadores, TELAS_PERMITIDAS_NO_DIST } from "./marcadores-dist";

describe("marcadores no dist", () => {
  it("reprova um dist de exemplo com o marcador", () => {
    expect(TELAS_PERMITIDAS_NO_DIST).toEqual([]);
    const exemplo = path.join(raizFront, "tests/v7/fixtures/dist-com-marcador");
    const achados = procurarMarcadores(exemplo);
    expect(achados.length).toBeGreaterThan(0);
    expect(achados[0]?.marcas).toContain("__HZ_V7_101__");
    expect(marcadoresProibidos("tela __HZ_V7_98__")).toEqual(["__HZ_V7_98__"]);
  });

  it("o build sem a flag não contém marcador __HZ_V7_", () => {
    const dist = path.join(raizFront, "dist");
    if (existsSync(dist)) rmSync(dist, { recursive: true, force: true });
    const ambiente = { ...process.env, VITE_V7_VITRINE: "" };
    execFileSync(process.execPath, [path.join(raizFront, "node_modules/typescript/lib/tsc.js"), "-b"], {
      cwd: raizFront,
      env: ambiente,
      stdio: "pipe",
    });
    execFileSync(process.execPath, [path.join(raizFront, "node_modules/vite/bin/vite.js"), "build"], {
      cwd: raizFront,
      env: ambiente,
      stdio: "pipe",
    });
    expect(procurarMarcadores(dist)).toEqual([]);
  }, 180_000);
});
