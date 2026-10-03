/**
 * Build com base /app/ e copia dist → ../web/app (SPA do Render).
 */
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const raiz = fileURLToPath(new URL("..", import.meta.url));
const dist = join(raiz, "dist");
const dest = join(raiz, "..", "web", "app");

const build = spawnSync("npm", ["run", "build"], {
  cwd: raiz,
  stdio: "inherit",
  shell: true,
  env: { ...process.env, VITE_BASE: "/app/" },
});
if (build.status !== 0) process.exit(build.status ?? 1);

if (!existsSync(dist)) {
  console.error("dist ausente após o build");
  process.exit(1);
}

mkdirSync(dest, { recursive: true });
for (const nome of readdirSync(dest)) {
  rmSync(join(dest, nome), { recursive: true, force: true });
}
cpSync(dist, dest, { recursive: true });
console.log(`publicado: ${dest}`);
