/**
 * Build para Cloudflare Pages (VITE_BASE=/). Saída em dist/.
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const raiz = fileURLToPath(new URL("..", import.meta.url));

const tsc = spawnSync("npx", ["tsc", "-b"], {
  cwd: raiz,
  stdio: "inherit",
  shell: true,
});
if (tsc.status !== 0) process.exit(tsc.status ?? 1);

const vite = spawnSync("npx", ["vite", "build"], {
  cwd: raiz,
  stdio: "inherit",
  shell: true,
  env: { ...process.env, VITE_BASE: "/" },
});
process.exit(vite.status ?? 1);
