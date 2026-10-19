import { resolve } from "node:path";
import { defineConfig } from "vite";

/** Entrada só do teste visual. O build normal continua em vite.config.ts e no dist/. */
export default defineConfig({
  build: {
    outDir: "node_modules/.cache/v7-visual",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        "pagina-fixa": resolve("tests/v7/visual/pagina-fixa.html"),
        "pagina-fonte-inexistente": resolve("tests/v7/visual/pagina-fonte-inexistente.html"),
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
  },
});
