// Pós-build do export estático (Next 16): o cliente pede os segmentos RSC com
// nome plano (ex.: explorar/__next.explorar.__PAGE__.txt), mas o export grava em
// subpasta (explorar/__next.explorar/__PAGE__.txt). Copiamos para o nome plano
// para evitar 404 no prefetch (local e no Cloudflare Pages).
import { copyFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const OUT = new URL("../out/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
let n = 0;

function achatar(dirSeg, prefixo, destino) {
  for (const nome of readdirSync(dirSeg)) {
    const p = join(dirSeg, nome);
    if (statSync(p).isDirectory()) achatar(p, `${prefixo}.${nome}`, destino);
    else {
      copyFileSync(p, join(destino, `${prefixo}.${nome}`));
      n++;
    }
  }
}

function varrer(dir) {
  for (const nome of readdirSync(dir)) {
    const p = join(dir, nome);
    if (!statSync(p).isDirectory()) continue;
    if (nome.startsWith("__next.")) achatar(p, nome, dir);
    else if (nome !== "_next") varrer(p);
  }
}

varrer(OUT);
console.log(`corrigir-rsc-export: ${n} arquivo(s) de segmento copiados`);
