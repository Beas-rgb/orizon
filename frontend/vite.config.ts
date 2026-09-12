import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/projetos": "http://127.0.0.1:8000",
      "/pesquisas": "http://127.0.0.1:8000",
      "/biblioteca": "http://127.0.0.1:8000",
      "/notificacoes": "http://127.0.0.1:8000",
      "/modelos": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/dev": "http://127.0.0.1:8000",
    },
  },
});
