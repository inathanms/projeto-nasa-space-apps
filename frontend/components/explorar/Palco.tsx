"use client";

import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { explorar } from "@/content/explorar";
import { clampDec, fmtGraus, fmtRaHm, wrapRa } from "@/lib/coords";
import TerraGlobo from "./TerraGlobo";
import s from "./explorar.module.css";

// ---------- geometria (viewBox 1000 × 700) ----------
const TX = -40; // centro da Terra (fora da tela, à esquerda)
const TY = 350;
const TR = 330; // raio da Terra
const AR = TR + 88; // raio do arco de rotação
const ANG = 58; // o arco vai de −58° a +58°
const SX = 640; // satélite (centro do corpo)
const SY = 330;

// Nave SPHEREx real: recorte do render oficial PIA26531 "SPHEREx in Orbit (Artist's Concept)",
// crédito NASA/JPL-Caltech. Região x 470, y 155, 1000×765 px da imagem 1920×1080, fundo removido
// por contorno → public/explorar/spherex-nave.png (600×459).
const SAT_IMG = "/explorar/spherex-nave.png";
const SAT_ESCALA = 0.33; // px do render → unidades do viewBox
const SAT_W = 1000 * SAT_ESCALA;
const SAT_H = 765 * SAT_ESCALA;
const SAT_CORPO = { x: 494 * SAT_ESCALA, y: 365 * SAT_ESCALA }; // pivô (meio do cone) dentro do recorte
// aro da abertura do cone (elipse 486×72 px no render), relativo ao pivô
const SAT_ARO = { meia: 486 * SAT_ESCALA, y: -284 * SAT_ESCALA };
const SAT_BASE = 64; // graus: eixo do telescópio apontando para o visor (à direita, um pouco acima)
const FEIXE_COMPR = 430; // comprimento do feixe ao longo do eixo
const FEIXE_ABRE = 26; // quanto o feixe abre de cada lado no fim

// gira um ponto (relativo ao pivô) e devolve a posição no palco
const girar = (x: number, y: number, graus: number) => {
  const c = Math.cos(rad(graus));
  const s = Math.sin(rad(graus));
  return { x: r2(SX + x * c - y * s), y: r2(SY + x * s + y * c) };
};

const rad = (g: number) => (g * Math.PI) / 180;
const raParaAng = (ra: number) => -ANG + (wrapRa(ra) / 360) * 2 * ANG;
const angParaRa = (a: number) => wrapRa(((Math.max(-ANG, Math.min(ANG, a)) + ANG) / (2 * ANG)) * 360);
// arredondado: seno/cosseno podem diferir na última casa entre servidor e navegador (hydration)
const r2 = (v: number) => Math.round(v * 100) / 100;
const noArco = (a: number, r = AR) => ({ x: r2(TX + r * Math.cos(rad(a))), y: r2(TY + r * Math.sin(rad(a))) });

// arrastar a Terra na horizontal: graus de RA por unidade do viewBox (1 volta = circunferência)
const RA_POR_UNIDADE = 360 / (2 * Math.PI * TR);

const ARCO_D = (() => {
  const a = noArco(-ANG);
  const b = noArco(ANG);
  return `M${a.x} ${a.y} A${AR} ${AR} 0 0 1 ${b.x} ${b.y}`;
})();

type Props = {
  ra: number;
  dec: number;
  onRa: (ra: number) => void;
  onDec: (dec: number) => void;
};

export default function Palco({ ra, dec, onRa, onDec }: Props) {
  const svg = useRef<SVGSVGElement>(null);
  const arr = useRef<{ tipo: string; x: number; y: number } | null>(null);
  const t = explorar;

  const paraSvg = (cx: number, cy: number) => {
    const m = svg.current?.getScreenCTM();
    if (!m) return { x: 0, y: 0, k: 1 };
    const p = new DOMPoint(cx, cy).matrixTransform(m.inverse());
    return { x: p.x, y: p.y, k: m.a };
  };

  function down(e: PointerEvent<SVGSVGElement>) {
    const tipo = (e.target as Element).closest("[data-arraste]")?.getAttribute("data-arraste");
    if (!tipo) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    arr.current = { tipo, x: e.clientX, y: e.clientY };
    if (tipo === "arco") moverArco(e.clientX, e.clientY);
  }
  function moverArco(cx: number, cy: number) {
    const p = paraSvg(cx, cy);
    onRa(angParaRa((Math.atan2(p.y - TY, p.x - TX) * 180) / Math.PI));
  }
  function move(e: PointerEvent<SVGSVGElement>) {
    const a = arr.current;
    if (!a) return;
    const { k } = paraSvg(e.clientX, e.clientY);
    if (a.tipo === "arco") moverArco(e.clientX, e.clientY);
    else if (a.tipo === "terra") onRa(wrapRa(ra - ((e.clientX - a.x) / k) * RA_POR_UNIDADE));
    else if (a.tipo === "sat") onDec(clampDec(dec - ((e.clientY - a.y) / k) * 0.5));
    a.x = e.clientX;
    a.y = e.clientY;
  }
  function up(e: PointerEvent<SVGSVGElement>) {
    if (!arr.current) return;
    arr.current = null;
    e.currentTarget.releasePointerCapture(e.pointerId);
  }

  function teclaArco(e: KeyboardEvent) {
    const p = e.shiftKey ? 15 : 1;
    const mapa: Record<string, number> = { ArrowDown: p, ArrowRight: p, PageDown: 15, ArrowUp: -p, ArrowLeft: -p, PageUp: -15 };
    if (!(e.key in mapa)) return;
    e.preventDefault();
    onRa(wrapRa(Math.round(ra + mapa[e.key])));
  }

  const ang = raParaAng(ra);
  const h = noArco(ang);
  const trilhaD = (() => {
    const a = noArco(ang);
    const b = noArco(Math.min(ANG, ang + 20));
    return `M${a.x} ${a.y} A${AR} ${AR} 0 0 1 ${b.x} ${b.y}`;
  })();

  // Dec maior = telescópio aponta mais para cima
  const inclinacao = SAT_BASE - dec * 0.3;
  // feixe = campo de visão saindo das duas pontas do aro, ao longo do eixo do cone
  const { meia, y: yAro } = SAT_ARO;
  const feixe = [
    girar(-meia, yAro, inclinacao),
    girar(meia, yAro, inclinacao),
    girar(meia + FEIXE_ABRE, yAro - FEIXE_COMPR, inclinacao),
    girar(-meia - FEIXE_ABRE, yAro - FEIXE_COMPR, inclinacao),
  ];
  const meioAro = girar(0, yAro, inclinacao);
  const fimFeixe = girar(0, yAro - FEIXE_COMPR, inclinacao);

  return (
    <svg
      ref={svg}
      className={s.palco}
      viewBox="0 0 1000 700"
      preserveAspectRatio="xMinYMid meet"
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
    >
      <defs>
        <radialGradient id="oceano" cx="62%" cy="38%" r="75%">
          <stop offset="0" stopColor="#2f6fc0" />
          <stop offset=".55" stopColor="#173f7c" />
          <stop offset="1" stopColor="#081a3c" />
        </radialGradient>
        <radialGradient id="atmosferaTerra" cx="50%" cy="50%" r="50%">
          <stop offset=".93" stopColor="#7ab8ff" stopOpacity="0" />
          <stop offset=".985" stopColor="#7ab8ff" stopOpacity=".35" />
          <stop offset="1" stopColor="#bfe0ff" stopOpacity=".7" />
        </radialGradient>
        <filter id="halo" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="14" />
        </filter>
        <linearGradient id="feixe" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="var(--acc-l)" stopOpacity=".45" />
          <stop offset="1" stopColor="var(--acc-l)" stopOpacity="0" />
        </linearGradient>
        <marker id="ponta" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 Z" fill="var(--acc-l)" />
        </marker>
      </defs>

      {/* feixe do satélite até o visor (à direita) */}
      <linearGradient id="feixeEixo" gradientUnits="userSpaceOnUse" x1={meioAro.x} y1={meioAro.y} x2={fimFeixe.x} y2={fimFeixe.y}>
        <stop offset="0" stopColor="var(--acc-l)" stopOpacity=".34" />
        <stop offset=".7" stopColor="var(--acc-l)" stopOpacity=".08" />
        <stop offset="1" stopColor="var(--acc-l)" stopOpacity="0" />
      </linearGradient>
      <polygon points={feixe.map((p) => `${p.x},${p.y}`).join(" ")} fill="url(#feixeEixo)" aria-hidden="true" />

      {/* ---------- Terra ---------- */}
      <g aria-hidden="true">
        <circle cx={TX} cy={TY} r={TR + 18} fill="#5aa0ff" opacity=".35" filter="url(#halo)" />
        <g data-arraste="terra" className={s.terra}>
          {/* base (aparece até a textura carregar) */}
          <circle cx={TX} cy={TY} r={TR} fill="url(#oceano)" />
          {/* imagem de satélite real projetada na esfera (NASA Blue Marble) */}
          <TerraGlobo cx={TX} cy={TY} r={TR} x0={-30} y0={TY - TR} largura={TX + TR + 30} altura={2 * TR} longitude={ra} />
          <circle cx={TX} cy={TY} r={TR} fill="url(#atmosferaTerra)" pointerEvents="none" />
          <circle cx={TX} cy={TY} r={TR + 2} fill="none" stroke="#8cc4ff" strokeOpacity=".7" strokeWidth="3" />
        </g>
      </g>

      {/* ---------- arco "Rotação da Terra" ---------- */}
      <path d={ARCO_D} className={s.arco} aria-hidden="true" />
      <path d={trilhaD} className={s.arcoAtivo} aria-hidden="true" />
      <circle cx={noArco(-ANG).x} cy={noArco(-ANG).y} r={5} className={s.arcoPonta} aria-hidden="true" />
      <circle cx={noArco(ANG).x} cy={noArco(ANG).y} r={5} className={s.arcoPonta} aria-hidden="true" />
      <path d={ARCO_D} className={s.arcoAlvo} data-arraste="arco" aria-hidden="true" />

      <g className={s.arcoRotulo} transform={`translate(${h.x + 28} ${h.y - 52})`} aria-hidden="true">
        <text x={0} y={0} className={s.rotulo}>{t.terra.rotulo}</text>
        <text x={0} y={22} className={s.rotuloSub}>{t.terra.eixo} {fmtRaHm(ra)}</text>
        <path d={`M-28 52 H-8 V34`} className={s.arcoLider} />
        <rect x={0} y={34} width={118} height={40} rx={9} className={s.valorCaixa} />
        <text x={59} y={61} textAnchor="middle" className={s.valor}>{fmtGraus(ra)}</text>
      </g>

      <circle
        cx={h.x}
        cy={h.y}
        r={11}
        className={s.alca}
        data-arraste="arco"
        role="slider"
        tabIndex={0}
        aria-label={t.terra.slider}
        aria-valuemin={0}
        aria-valuemax={360}
        aria-valuenow={Math.round(ra * 100) / 100}
        aria-valuetext={`RA ${fmtGraus(ra)}, ${fmtRaHm(ra)}`}
        onKeyDown={teclaArco}
      />

      {/* ---------- satélite ---------- */}
      <g className={s.chip} transform={`translate(${SX - 262} ${SY - 206})`} aria-hidden="true">
        <rect width={136} height={38} rx={10} />
        <g transform="translate(16 11) scale(.8)" className={s.chipIcone}>
          <rect x="7" y="7" width="8" height="8" rx="1.5" />
          <path d="M3 3l4 4M15 15l4 4M0 6l6-6M16 22l6-6" />
        </g>
        <text x={46} y={25}>{t.satelite.nome}</text>
      </g>

      <g data-arraste="sat" className={s.satelite} transform={`translate(${SX} ${SY}) rotate(${inclinacao.toFixed(2)})`} aria-hidden="true">
        <image
          href={SAT_IMG}
          x={-SAT_CORPO.x}
          y={-SAT_CORPO.y}
          width={SAT_W}
          height={SAT_H}
          preserveAspectRatio="none"
        />
      </g>

      {/* setas curvas da inclinação */}
      <path
        d={`M${SX + 146} ${SY + 122} A190 190 0 0 1 ${SX - 95} ${SY + 165}`}
        className={s.setaCurva}
        markerStart="url(#ponta)"
        markerEnd="url(#ponta)"
        aria-hidden="true"
      />
    </svg>
  );
}
