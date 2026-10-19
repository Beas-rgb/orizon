import { defineConfig } from "@playwright/test";

const comum = {
  timezoneId: "America/Sao_Paulo",
  locale: "pt-BR",
  colorScheme: "light" as const,
  reducedMotion: "reduce" as const,
  deviceScaleFactor: 2,
};

export default defineConfig({
  testDir: "tests/v7/visual",
  workers: 1,
  retries: 0,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:4173",
    ...comum,
  },
  webServer: {
    command: "npx vite build --config vite.visual.config.ts && npx vite preview --config vite.visual.config.ts --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173/tests/v7/visual/pagina-fixa.html",
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    {
      name: "celular",
      testMatch: /determinismo\.spec\.ts/,
      use: { ...comum, viewport: { width: 390, height: 1414 } },
    },
    {
      name: "desktop",
      testMatch: /determinismo\.spec\.ts/,
      use: { ...comum, viewport: { width: 1440, height: 1414 } },
    },
    {
      name: "calibracao",
      testMatch: /calibracao\.spec\.ts/,
    },
  ],
});
