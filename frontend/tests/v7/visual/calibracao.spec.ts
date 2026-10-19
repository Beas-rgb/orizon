import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { test } from "@playwright/test";
import { PNG } from "pngjs";
import { comparar, type Imagem } from "../comparador/comparar";

type Linha = { nome: string; tela: string; largura: string; dimensoes: string; sha256: string };

function lerManifesto(): Linha[] {
  return readFileSync(path.resolve("tests/v7/manifesto.json"), "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((linha) => JSON.parse(linha) as Linha);
}

function paraImagem(png: PNG): Imagem {
  return {
    largura: png.width,
    altura: png.height,
    pixels: new Uint8ClampedArray(png.data),
  };
}

test("calibração só registra o pipeline", async ({}, info) => {
  const pasta = process.env.HZ_REFERENCIAS_DIR;
  if (!pasta) {
    test.skip(true, "defina HZ_REFERENCIAS_DIR");
    return;
  }
  const saida = process.env.HZ_CALIBRACAO_SAIDA ?? path.join(process.env.TEMP ?? "/tmp", "calibracao-v7");
  mkdirSync(saida, { recursive: true });
  const data = new Date().toISOString().slice(0, 10);
  const linhas = lerManifesto();
  const relatorio = [];
  for (const item of linhas) {
    const arquivo = path.join(pasta, item.nome);
    let registro: Record<string, unknown> = { nome: item.nome, tela: item.tela, largura: item.largura };
    try {
      const bytes = readFileSync(arquivo);
      const hash = createHash("sha256").update(bytes).digest("hex");
      const png = PNG.sync.read(bytes);
      const [largura, altura] = item.dimensoes.split("x").map(Number);
      const imagem = paraImagem(png);
      const resultado = comparar(imagem, imagem);
      registro = {
        ...registro,
        sha256ok: hash === item.sha256,
        dimensoesOk: png.width === largura && png.height === altura,
        percentual: resultado.percentual,
        manchaLargura: resultado.manchaLargura,
        manchaAltura: resultado.manchaAltura,
      };
    } catch (erro) {
      registro = { ...registro, erro: erro instanceof Error ? erro.message : "falha" };
    }
    relatorio.push(registro);
    info.annotations.push({ type: item.nome, description: JSON.stringify(registro) });
  }
  writeFileSync(path.join(saida, `calibracao-${data}.json`), JSON.stringify(relatorio, null, 2));
  const md = ["# Calibração", "", ...relatorio.map((item) => `- ${JSON.stringify(item)}`), ""].join("\n");
  writeFileSync(path.join(saida, `calibracao-${data}.md`), md);
});
