"use client";

import { explorar } from "@/content/explorar";
import type { Sequence } from "@/types/sequence";
import s from "./explorar.module.css";

type Props = {
  seq: Sequence | null;
  idx: number;
  tocando: boolean;
  modo: "data" | "mjd";
  onModo: (m: "data" | "mjd") => void;
  onIdx: (i: number) => void;
  onPasso: (p: number) => void;
  onTocar: () => void;
};

const dataFmt = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC" });
const horaFmt = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "UTC" });
const mjdFmt = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 5, maximumFractionDigits: 5 });
const mjd = (ms: number) => ms / 86_400_000 + 40_587;

const Ic = {
  relogio: <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>,
  calendario: <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15" rx="2" /><path d="M3.5 10h17M8 3v4M16 3v4" /></svg>,
  hash: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4 7 20M17 4l-2 16M4 9h17M3 15h17" /></svg>,
  play: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" className={s.icCheio} /></svg>,
  pausa: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" className={s.icCheio} /></svg>,
  voltar: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 6 4 12l7 6zM20 6l-7 6 7 6z" className={s.icCheio} /></svg>,
  avancar: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m13 6 7 6-7 6zM4 6l7 6-7 6z" className={s.icCheio} /></svg>,
};

export default function BarraTempo({ seq, idx, tocando, modo, onModo, onIdx, onPasso, onTocar }: Props) {
  const t = explorar.tempo;
  const frames = seq?.frames ?? [];
  const n = frames.length;
  const tempos = frames.map((f) => Date.parse(f.observed_at_utc));
  const atual = tempos[idx];
  const min = tempos[0] ?? 0;
  const max = tempos[n - 1] ?? 1;
  const span = Math.max(1, max - min);
  const pct = n > 1 ? ((atual - min) / span) * 100 : 0;
  const ok = n > 0;

  function escolher(v: number) {
    let melhor = 0;
    tempos.forEach((tm, i) => {
      if (Math.abs(tm - v) < Math.abs(tempos[melhor] - v)) melhor = i;
    });
    onIdx(melhor);
  }

  const Spin = ({ rotulo }: { rotulo: string }) => (
    <span className={s.spin}>
      <button type="button" onClick={() => onPasso(1)} disabled={n < 2} aria-label={`${rotulo}: ${t.proxima}`}>
        ▲
      </button>
      <button type="button" onClick={() => onPasso(-1)} disabled={n < 2} aria-label={`${rotulo}: ${t.anterior}`}>
        ▼
      </button>
    </span>
  );

  return (
    <section className={s.tempo} aria-label={t.titulo}>
      <h2 className={s.tempoTitulo}>
        {Ic.relogio}
        {t.titulo}
      </h2>

      <div className={s.segmento} role="radiogroup" aria-label={t.titulo}>
        <button type="button" role="radio" aria-checked={modo === "data"} onClick={() => onModo("data")}>
          {Ic.calendario}
          {t.dataHora}
        </button>
        <button type="button" role="radio" aria-checked={modo === "mjd"} onClick={() => onModo("mjd")}>
          {Ic.hash}
          {t.mjd}
        </button>
      </div>

      {modo === "data" ? (
        <>
          <div className={s.campoTempo}>
            {Ic.calendario}
            <output aria-label={t.data}>{ok ? dataFmt.format(atual) : t.semDados}</output>
            <Spin rotulo={t.data} />
          </div>
          <div className={s.campoTempo}>
            {Ic.relogio}
            <output aria-label={t.hora}>{ok ? horaFmt.format(atual) : t.semDados}</output>
            <Spin rotulo={t.hora} />
          </div>
        </>
      ) : (
        <div className={`${s.campoTempo} ${s.campoMjd}`}>
          {Ic.hash}
          <output aria-label={t.mjdRotulo}>{ok ? mjdFmt.format(mjd(atual)) : t.semDados}</output>
          <Spin rotulo={t.mjdRotulo} />
        </div>
      )}

      <button
        type="button"
        className={s.btnPlay}
        onClick={onTocar}
        disabled={n < 2}
        aria-label={tocando ? t.pausar : t.play}
        aria-pressed={tocando}
      >
        {tocando ? Ic.pausa : Ic.play}
      </button>

      <div className={s.linhaTempo}>
        <button type="button" className={s.btnPasso} onClick={() => onPasso(-1)} disabled={n < 2} aria-label={t.anterior}>
          {Ic.voltar}
        </button>
        <div className={s.trilhaTempo}>
          <input
            type="range"
            min={min}
            max={max}
            step={1000}
            value={ok ? atual : min}
            disabled={n < 2}
            onChange={(e) => escolher(Number(e.target.value))}
            aria-label={t.linha}
            aria-valuetext={ok ? `${dataFmt.format(atual)} ${horaFmt.format(atual)} UTC` : t.semDados}
            style={{ ["--p" as string]: `${pct}%` }}
          />
          {n > 1 &&
            tempos.map((tm, i) => (
              <span
                key={i}
                className={`${s.marcaEpoca} ${i === idx ? s.marcaEpocaAtiva : ""}`}
                style={{ left: `${((tm - min) / span) * 100}%` }}
                aria-hidden="true"
              />
            ))}
        </div>
        <button type="button" className={s.btnPasso} onClick={() => onPasso(1)} disabled={n < 2} aria-label={t.proxima}>
          {Ic.avancar}
        </button>
      </div>
    </section>
  );
}
