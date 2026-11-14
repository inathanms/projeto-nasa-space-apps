import Link from "next/link";
import { hero } from "@/content/landing";
import Tumbleweed from "./Tumbleweed";
import s from "./landing.module.css";

// PRNG com seed fixa: as estrelas saem iguais em todo build (sem hydration mismatch).
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(2026);
const estrelas = Array.from({ length: 150 }, () => ({
  cx: +(rand() * 1440).toFixed(1),
  cy: +(rand() * 700).toFixed(1),
  r: +(rand() * 1.3 + 0.3).toFixed(2),
  o: +(rand() * 0.6 + 0.2).toFixed(2),
}));

function Ceu() {
  return (
    <svg className={s.sky} viewBox="0 0 1440 900" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">
      <g fill="#f7e1c9">
        {estrelas.map((e, i) => (
          <circle key={i} cx={e.cx} cy={e.cy} r={e.r} opacity={e.o} />
        ))}
      </g>
      {/* Dunas: 3 camadas */}
      <path d="M0 790 C220 760 420 800 640 830 S1040 800 1240 770 S1400 745 1440 750 L1440 900 L0 900Z" fill="#c75636" />
      <path d="M0 835 C240 815 460 835 680 850 S1060 835 1260 815 S1410 812 1440 815 L1440 900 L0 900Z" fill="#e0703a" />
      <path d="M0 868 C300 855 620 868 920 860 S1320 850 1440 856 L1440 900 L0 900Z" fill="#eb8c3e" />
    </svg>
  );
}

type Pos = { x: number; y: number };

function Foto({ titulo, src, plutao, antes, rotulo }: { titulo: string; src: string; plutao: Pos; antes?: Pos; rotulo?: string }) {
  const pct = (p: Pos) => ({ left: `${p.x * 100}%`, top: `${p.y * 100}%` });
  return (
    <figure className={`${s.foto} ${antes ? s.fotoAchou : ""}`}>
      <figcaption>{titulo}</figcaption>
      <div className={s.fotoPlaca}>
        <img src={src} alt="" width={720} height={720} loading="eager" />
        {antes && <span className={s.fotoAntes} style={pct(antes)} aria-hidden="true" />}
        <span className={`${s.fotoAlvo} ${antes ? s.fotoAlvoAchou : ""}`} style={pct(plutao)} aria-hidden="true" />
        {rotulo && (
          <span className={s.fotoRotulo} style={{ left: `${plutao.x * 100}%`, top: `calc(${plutao.y * 100}% + 24px)` }} aria-hidden="true">
            {rotulo}
          </span>
        )}
      </div>
    </figure>
  );
}

const IconeSelo = () => (
  <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
    <path d="M3 8.5 6.5 12 13 4.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const IconeProva = ({ tipo }: { tipo: "estrela" | "satelite" }) =>
  tipo === "estrela" ? (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="m12 2.5 2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.3l-5.9 3.2 1.2-6.5-4.8-4.6 6.6-.9z" fill="#eaa83a" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="9" y="9" width="6" height="6" rx="1" fill="#cfe3dc" />
      <path d="M2 4l6 6M16 14l6 6" stroke="#5fb3a1" strokeWidth="3" />
    </svg>
  );

export default function Hero() {
  return (
    <section id="inicio" className={s.hero} aria-labelledby="hero-titulo">
      <Ceu />
      <Tumbleweed />
      <div className={s.heroGrid}>
        <div className={s.heroText}>
          <p className={s.heroKicker}>{hero.kicker}</p>
          <h1 id="hero-titulo" className={s.h1}>
            {hero.titulo.map((l) => (
              <span key={l.texto} className={s.h1Linha}>
                {l.texto}
                {l.destaque && <em>{l.destaque}</em>}
              </span>
            ))}
          </h1>
          <p className={s.heroP}>{hero.texto}</p>

          <Link href={hero.cta.href} className={s.btnMega}>
            <svg className={s.megaEstrela} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M12 2c.7 5.4 2.6 7.3 8 8-5.4.7-7.3 2.6-8 8-.7-5.4-2.6-7.3-8-8 5.4-.7 7.3-2.6 8-8Z" fill="currentColor" />
            </svg>
            <span>{hero.cta.label}</span>
            <svg className={s.megaSeta} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M4 12h15M13 5l7 7-7 7" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </Link>

          <ul className={s.selos}>
            {hero.selos.map((x) => (
              <li key={x}>
                <IconeSelo />
                {x}
              </li>
            ))}
          </ul>
          <ul className={s.provas}>
            {hero.provas.map((p) => (
              <li key={p.forte}>
                <IconeProva tipo={p.icone} />
                <strong>{p.forte}</strong> {p.texto}
              </li>
            ))}
          </ul>
        </div>

        <figure className={s.fotosWrap}>
          <div className={s.fotos} role="img" aria-label={hero.fotos.rotulo}>
            <Foto titulo={hero.fotos.foto1.titulo} src={hero.fotos.foto1.src} plutao={hero.fotos.foto1.plutao} />
            <svg className={s.troca} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
              <path d="M5 11h21l-5-5M27 21H6l5 5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <Foto
              titulo={hero.fotos.foto2.titulo}
              src={hero.fotos.foto2.src}
              plutao={hero.fotos.foto2.plutao}
              antes={hero.fotos.foto1.plutao}
              rotulo={hero.fotos.achou}
            />
          </div>
          <figcaption className={s.fotosCredito}>
            <a href={hero.fotos.creditoHref} target="_blank" rel="noopener noreferrer">
              {hero.fotos.credito} ↗
            </a>
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
