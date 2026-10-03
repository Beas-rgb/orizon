/**
 * Substitui hex/rgba do legado por var(--hz-*). Rode depois de atualizar tokens.css.
 * Só altera arquivos listados em hex_legado.txt (exceto tokens.css).
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = fileURLToPath(new URL("..", import.meta.url));
const lista = join(raiz, "scripts", "hex_legado.txt");

const map = [
  ["#A02828", "var(--hz-danger)"],
  ["#a02828", "var(--hz-danger)"],
  ["#1E7A4A", "var(--hz-ok)"],
  ["#1e7a4a", "var(--hz-ok)"],
  ["#1f8a4c", "var(--hz-ok)"],
  ["#A07020", "var(--hz-warn)"],
  ["#a07020", "var(--hz-warn)"],
  ["#c47b12", "var(--hz-warn)"],
  ["#1D5FAF", "var(--hz-accent)"],
  ["#1d5faf", "var(--hz-accent)"],
  ["#164A8A", "var(--hz-accent-dark)"],
  ["#164a8a", "var(--hz-accent-dark)"],
  ["#171717", "var(--hz-ink)"],
  ["#111", "var(--hz-ink)"],
  ["#1c1c1c", "var(--hz-ink)"],
  ["#0F766E", "var(--hz-teal)"],
  ["#0f766e", "var(--hz-teal)"],
  ["#6b7280", "var(--hz-text-2)"],
  ["#4b5563", "var(--hz-text-2)"],
  ["#6d6d6d", "var(--hz-muted)"],
  ["#8a8a8a", "var(--hz-muted-2)"],
  ["#5c5c5c", "var(--hz-muted)"],
  ["#4B5C6E", "var(--hz-slate)"],
  ["#b00020", "var(--hz-danger)"],
  ["#ffffff", "var(--hz-surface)"],
  ["#fff", "var(--hz-surface)"],
  ["#1f2937", "var(--hz-body)"],
  ["#eef1f5", "var(--hz-canvas)"],
  ["#f4f3ef", "var(--hz-canvas-warm)"],
  ["#f3f2ee", "var(--hz-canvas-warm)"],
  ["#ddd", "var(--hz-line)"],
  ["#0a3d91", "var(--hz-primary)"],
  ["#082e6b", "var(--hz-primary-strong)"],
  ["#0b0f14", "var(--hz-text)"],
  ["#f8fafc", "var(--hz-bg)"],
  ["#10b981", "var(--hz-success)"],
  ["#f59e0b", "var(--hz-warning)"],
  ["#ef4444", "var(--hz-danger-bright)"],
  ["rgba(255,255,255,0.55)", "var(--hz-white-55)"],
  ["rgba(255,255,255,0.7)", "var(--hz-white-70)"],
  ["rgba(255,255,255,0.65)", "var(--hz-white-65)"],
  ["rgba(255,255,255,0.75)", "var(--hz-white-75)"],
  ["rgba(255, 255, 255, 0.75)", "var(--hz-white-75)"],
  ["rgba(255,255,255,0.6)", "var(--hz-white-60)"],
  ["rgba(255, 255, 255, 0.6)", "var(--hz-white-60)"],
  ["rgba(255,255,255,0.5)", "var(--hz-white-50)"],
  ["rgba(255, 255, 255, 0.45)", "var(--hz-white-45)"],
  ["rgba(29,95,175,0.10)", "var(--hz-accent-10)"],
  ["rgba(29,95,175,0.08)", "var(--hz-accent-08)"],
  ["rgba(29,95,175,0.12)", "var(--hz-accent-12)"],
  ["rgba(29,95,175,0.16)", "var(--hz-accent-16)"],
  ["rgba(29,95,175,0.18)", "var(--hz-accent-18)"],
  ["rgba(29,95,175,0.15)", "var(--hz-accent-15)"],
  ["rgba(29,95,175,0.20)", "var(--hz-accent-20)"],
  ["rgba(29,95,175,0.2)", "var(--hz-accent-20)"],
  ["rgba(29,95,175,0.22)", "var(--hz-accent-22)"],
  ["rgba(29,95,175,0.25)", "var(--hz-accent-25)"],
  ["rgba(29,95,175,0.28)", "var(--hz-accent-28)"],
  ["rgba(29,95,175,0.30)", "var(--hz-accent-30)"],
  ["rgba(29,95,175,0.3)", "var(--hz-accent-30)"],
  ["rgba(29,95,175,0.35)", "var(--hz-accent-35)"],
  ["rgba(29,95,175,0.09)", "var(--hz-accent-09)"],
  ["rgba(29,95,175,0.06)", "var(--hz-accent-06)"],
  ["rgba(30,122,74,0.20)", "var(--hz-ok-20)"],
  ["rgba(30,122,74,0.08)", "var(--hz-ok-08)"],
  ["rgba(30,122,74,0.12)", "var(--hz-ok-12)"],
  ["rgba(30,122,74,0.22)", "var(--hz-ok-22)"],
  ["rgba(30,122,74,0.10)", "var(--hz-ok-10)"],
  ["rgba(30,122,74,0.09)", "var(--hz-ok-09)"],
  ["rgba(30,122,74,0.3)", "var(--hz-ok-30)"],
  ["rgba(160,112,32,0.20)", "var(--hz-warn-20)"],
  ["rgba(160,112,32,0.12)", "var(--hz-warn-12)"],
  ["rgba(160,112,32,0.22)", "var(--hz-warn-22)"],
  ["rgba(160,112,32,0.10)", "var(--hz-warn-10)"],
  ["rgba(160,112,32,0.09)", "var(--hz-warn-09)"],
  ["rgba(160,112,32,0.35)", "var(--hz-warn-35)"],
  ["rgba(160,112,32,0.08)", "var(--hz-warn-08)"],
  ["rgba(160,112,32,0.1)", "var(--hz-warn-10)"],
  ["rgba(160,40,40,0.09)", "var(--hz-danger-09)"],
  ["rgba(160,40,40,0.20)", "var(--hz-danger-20)"],
  ["rgba(160,40,40,0.06)", "var(--hz-danger-06)"],
  ["rgba(15,118,110,0.25)", "var(--hz-teal-25)"],
  ["rgba(15,118,110,0.08)", "var(--hz-teal-08)"],
  ["rgba(75,92,110,0.09)", "var(--hz-slate-09)"],
  ["rgba(75,92,110,0.18)", "var(--hz-slate-18)"],
  ["rgba(0,0,0,0.05)", "var(--hz-black-05)"],
  ["rgba(0,0,0,0.06)", "var(--hz-black-06)"],
  ["rgba(0,0,0,0.07)", "var(--hz-black-07)"],
  ["rgba(0,0,0,0.08)", "var(--hz-black-08)"],
  ["rgba(0, 0, 0, 0.08)", "var(--hz-black-08)"],
  ["rgba(0,0,0,0.12)", "var(--hz-black-12)"],
  ["rgba(0,0,0,0.04)", "var(--hz-black-04)"],
  ["rgba(0,0,0,0.14)", "var(--hz-black-14)"],
  ["rgba(0, 0, 0, 0.14)", "var(--hz-black-14)"],
  ["rgba(22,74,138,0.07)", "var(--hz-accent-dark-07)"],
  ["rgba(20,30,50,0.20)", "var(--hz-navy-20)"],
  ["rgba(238,242,248,0.80)", "var(--hz-mist-80)"],
  ["rgba(240,244,250,0.88)", "var(--hz-mist-88)"],
  ["rgba(244,247,252,0.92)", "var(--hz-mist-92)"],
  ["rgba(244, 247, 252, 0.92)", "var(--hz-mist-92)"],
].sort((a, b) => b[0].length - a[0].length);

const legado = readFileSync(lista, "utf8")
  .split(/\r?\n/)
  .map((l) => l.trim())
  .filter((l) => l && !l.startsWith("#"));

const re = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/;
const still = [];

for (const rel of legado) {
  if (rel === "src/styles/tokens.css") continue;
  const p = join(raiz, rel);
  if (!existsSync(p)) {
    console.log("missing", rel);
    continue;
  }
  let text = readFileSync(p, "utf8");
  const orig = text;
  for (const [from, to] of map) {
    if (text.includes(from)) text = text.split(from).join(to);
  }
  if (text !== orig) {
    writeFileSync(p, text);
    console.log("updated", rel);
  }
  if (re.test(text)) still.push(rel);
}

writeFileSync(
  lista,
  still.length ? `${still.join("\n")}\n` : "# legado vazio\n",
);
console.log(`ainda com cor solta: ${still.length}`);
for (const s of still) console.log(s);
