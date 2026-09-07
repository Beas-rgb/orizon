import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/projetos": "http://127.0.0.1:8000",
      "/pesquisas": "http://127.0.0.1:8000",
      "/modelos": "http://127.0.0.1:8000",
      "/biblioteca": "http://127.0.0.1:8000",
      "/notificacoes": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
