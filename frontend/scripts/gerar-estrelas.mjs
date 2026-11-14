// Gera os blocos de estrelas (SVG) do fundo "universo" (.bg-universo).
//   node scripts/gerar-estrelas.mjs
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const pasta = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "fundo");
mkdirSync(pasta, { recursive: true });

function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const cores = ["#ffffff", "#f7e1c9", "#cfe3dc", "#fff3c4", "#bcd4ff"];

function bloco(nome, seed, tam, qtd, rMax, opMax) {
  const r = mulberry32(seed);
  const pts = Array.from({ length: qtd }, () => {
    const raio = r() < 0.08 ? 1 + r() * rMax : 0.35 + r() * 0.75;
    return `<circle cx="${(r() * tam).toFixed(1)}" cy="${(r() * tam).toFixed(1)}" r="${raio.toFixed(2)}" fill="${cores[Math.floor(r() * cores.length)]}" opacity="${(0.25 + r() * opMax).toFixed(2)}"/>`;
  });
  writeFileSync(join(pasta, nome), `<svg xmlns="http://www.w3.org/2000/svg" width="${tam}" height="${tam}" viewBox="0 0 ${tam} ${tam}">${pts.join("")}</svg>\n`);
  console.log("ok", nome);
}

bloco("estrelas-1.svg", 7, 997, 230, 1.1, 0.75);
bloco("estrelas-2.svg", 19, 613, 110, 0.6, 0.4);
