// Gera quadros SINTÉTICOS de teste para desenvolver o explorador
// enquanto os recortes reais do SPHEREx (P4) não chegam.
//
//   node scripts/gerar-exemplos-sinteticos.mjs
//
// Saída: public/examples/<slug>/manifest.json + frame-1.svg + frame-2.svg
// Todos os manifests saem com "is_synthetic": true e a UI exibe um aviso.
// Para trocar por dados reais: substituir a pasta do alvo por manifest.json + PNGs
// no mesmo formato (types/sequence.ts) e remover "is_synthetic".
// Plano: conteúdo sintético fica FORA da demo final.

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "examples");
const T = 400; // px

function mulberry32(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Cada alvo: estrelas de campo fixas + fonte(s) que mudam entre as épocas.
// pos em fração do quadro (0..1); r = raio do núcleo em px; b = brilho 0..1
const alvos = [
  {
    slug: "barnard", ra: 269.4521, dec: 4.6934, seed: 11,
    datas: ["2025-05-14T03:12:40Z", "2025-11-09T21:47:05Z"],
    fontes: [[{ x: 0.47, y: 0.53, r: 11, b: 1, cor: "#fff3d6" }], [{ x: 0.53, y: 0.45, r: 11, b: 1, cor: "#fff3d6" }]],
  },
  {
    slug: "wise0855", ra: 133.7951, dec: -7.2451, seed: 23,
    datas: ["2025-04-28T10:05:11Z", "2025-10-24T08:31:52Z"],
    fontes: [[{ x: 0.49, y: 0.51, r: 5, b: 0.75, cor: "#ff9a6b" }], [{ x: 0.53, y: 0.47, r: 5, b: 0.75, cor: "#ff9a6b" }]],
  },
  {
    slug: "eps-indi-b", ra: 331.0438, dec: -56.7828, seed: 37,
    datas: ["2025-06-02T17:20:03Z", "2025-12-01T14:02:44Z"],
    fontes: [
      [{ x: 0.47, y: 0.5, r: 6, b: 0.85, cor: "#ffae7a" }, { x: 0.515, y: 0.505, r: 5, b: 0.7, cor: "#ff8c5a" }],
      [{ x: 0.5, y: 0.47, r: 6, b: 0.85, cor: "#ffae7a" }, { x: 0.535, y: 0.48, r: 5, b: 0.7, cor: "#ff8c5a" }],
    ],
  },
  {
    slug: "rw-aur", ra: 76.9564, dec: 30.4014, seed: 41,
    datas: ["2025-03-19T06:44:18Z", "2025-09-13T02:15:37Z"],
    fontes: [[{ x: 0.5, y: 0.5, r: 7, b: 0.55, cor: "#ffe2a8" }], [{ x: 0.5, y: 0.5, r: 12, b: 1, cor: "#ffe2a8" }]],
  },
  {
    slug: "r-dra", ra: 248.1674, dec: 66.755, seed: 53,
    datas: ["2025-05-30T12:09:56Z", "2025-11-25T09:38:21Z"],
    fontes: [[{ x: 0.5, y: 0.5, r: 14, b: 1, cor: "#ffc27a" }], [{ x: 0.5, y: 0.5, r: 6, b: 0.45, cor: "#ffc27a" }]],
  },
];

function estrela(x, y, r, b, cor, id) {
  const halo = (r * 3.2).toFixed(1);
  return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${halo}" fill="url(#psf-${id})" opacity="${b.toFixed(2)}"/>
<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r * 0.45).toFixed(1)}" fill="${cor}" opacity="${Math.min(1, b + 0.1).toFixed(2)}"/>`;
}

function quadro(alvo, i) {
  const rand = mulberry32(alvo.seed);
  const campo = Array.from({ length: 70 }, () => ({
    x: rand() * T,
    y: rand() * T,
    r: rand() < 0.12 ? 3 + rand() * 4 : 0.8 + rand() * 1.8,
    b: 0.35 + rand() * 0.6,
  }));
  const defs = [];
  const corpo = [];
  campo.forEach((s, k) => {
    defs.push(`<radialGradient id="psf-c${k}"><stop offset="0" stop-color="#ffffff"/><stop offset=".25" stop-color="#e8f0ff" stop-opacity=".5"/><stop offset="1" stop-color="#e8f0ff" stop-opacity="0"/></radialGradient>`);
    corpo.push(estrela(s.x, s.y, s.r, s.b, "#ffffff", `c${k}`));
  });
  alvo.fontes[i].forEach((f, k) => {
    defs.push(`<radialGradient id="psf-a${k}"><stop offset="0" stop-color="${f.cor}"/><stop offset=".3" stop-color="${f.cor}" stop-opacity=".55"/><stop offset="1" stop-color="${f.cor}" stop-opacity="0"/></radialGradient>`);
    corpo.push(estrela(f.x * T, f.y * T, f.r, f.b, f.cor, `a${k}`));
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${T}" height="${T}" viewBox="0 0 ${T} ${T}">
<!-- QUADRO SINTÉTICO DE TESTE (não é dado do SPHEREx) -->
<defs>${defs.join("")}
<filter id="grao"><feTurbulence type="fractalNoise" baseFrequency="1.6" numOctaves="1" seed="${alvo.seed + i}"/><feColorMatrix values="0 0 0 0 .55  0 0 0 0 .6  0 0 0 0 .75  0 0 0 .22 0"/></filter></defs>
<rect width="${T}" height="${T}" fill="#03060c"/>
<rect width="${T}" height="${T}" filter="url(#grao)"/>
${corpo.join("\n")}
</svg>`;
}

for (const alvo of alvos) {
  const pasta = join(raiz, alvo.slug);
  mkdirSync(pasta, { recursive: true });
  const frames = alvo.datas.map((data, i) => {
    writeFileSync(join(pasta, `frame-${i + 1}.svg`), quadro(alvo, i));
    const principal = alvo.fontes[i][0];
    return {
      frame_id: `sintetico-${alvo.slug}-${i + 1}`,
      observed_at_utc: data,
      collection: "teste_sintetico",
      detector: 2,
      wavelength_um: 1.65,
      bandwidth_um: 0.04,
      calibration_version: "n/a",
      source_url: null,
      cutout_url: null,
      valid_fraction: 1,
      image_src: `frame-${i + 1}.svg`,
      marker: { x: principal.x, y: principal.y },
    };
  });
  const manifest = {
    sequence_id: `exemplo-sintetico-${alvo.slug}`,
    ra_deg: alvo.ra,
    dec_deg: alvo.dec,
    fov_arcmin: 6,
    collections: ["teste_sintetico"],
    fetched_at_utc: "2026-11-14T00:00:00Z",
    generated_at_utc: "2026-11-14T00:00:00Z",
    processing_version: "sintetico-0",
    is_synthetic: true,
    frames,
  };
  writeFileSync(join(pasta, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  console.log(`ok  ${alvo.slug}`);
}
