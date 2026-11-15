"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useRef, useState, type PointerEvent } from "react";
import { axisHint, CAPTURE_RADIUS, clamp, nearestTarget, scanPath, wrap, type Target } from "../../lib/pointing";
import SceneLoading from "../ui/SceneLoading";
import { targetInfo } from "../../content/target-info";
import TargetSheet from "./target-sheet";

const SceneCanvas = dynamic(() => import("../ui/SceneCanvas"), { ssr: false, loading: SceneLoading });

type Acquisition = { item: Target; before: { ra: number; dec: number }; isNew: boolean };
const DAY = 86_400_000;
const HOUR = 3_600_000;
const MJD_AT_UNIX = 40587;
const REFERENCE = Date.parse("2025-04-27T16:58:48.188Z");
const LIMIT_START = Date.parse("1900-01-01T00:00:00Z");
const LIMIT_END = Date.parse("2100-12-31T23:59:59Z");
const SIGNAL_SCALE = CAPTURE_RADIUS * 3;
const CAPTURE_PAUSE = 1600;
const LOGBOOK_KEY = "spherex:observatory:discoveries:v1";
const angleLabel = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const exactAngle = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 6 });

export default function Observatory({ targets }: { targets: Target[] }) {
  const [target, setTarget] = useState<string | null>(null);
  const [lockedTarget, setLockedTarget] = useState<Target | null>(null);
  const [aimPaused, setAimPaused] = useState(false);
  const [discovered, setDiscovered] = useState<string[]>([]);
  const [acquisition, setAcquisition] = useState<Acquisition | null>(null);
  const [ra, setRA] = useState(23.44);
  const [dec, setDec] = useState(42);
  const [time, setTime] = useState(REFERENCE);
  const [timeBounds, setTimeBounds] = useState(() => {
    const dates = [REFERENCE, ...targets.map((item) => Date.parse(item.time))];
    return { start: Math.min(...dates) - DAY, end: Math.max(...dates) + DAY };
  });
  const [mode, setMode] = useState<"utc" | "mjd">("utc");
  const [mjdDraft, setMjdDraft] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [sheet, setSheet] = useState<Target | null>(null);
  const pointer = useRef<{ id: number; x: number; y: number; ra: number; dec: number; lastX: number } | null>(null);
  const pauseTimer = useRef<number | null>(null);
  const rangeGesture = useRef<{ id: number; interrupted: boolean } | null>(null);
  const signal = nearestTarget(ra, dec, targets, (item) => discovered.includes(item.slug) || item.slug === lockedTarget?.slug);
  const raAdjusted = acquisition !== null && acquisition.before.ra !== acquisition.item.ra;
  const decAdjusted = acquisition !== null && acquisition.before.dec !== acquisition.item.dec;

  useEffect(() => {
    try {
      const stored: unknown = JSON.parse(window.localStorage.getItem(LOGBOOK_KEY) ?? "[]");
      if (Array.isArray(stored)) {
        setDiscovered(targets.filter((item) => stored.includes(item.slug)).map((item) => item.slug));
      }
    } catch { /* The logbook still works for the current visit. */ }
  }, [targets]);

  function captureTarget(item: Target, before: Acquisition["before"]) {
    if (rangeGesture.current) rangeGesture.current.interrupted = true;
    selectTarget(item);
    setAimPaused(true);
    pauseTimer.current = window.setTimeout(() => {
      pauseTimer.current = null;
      setAimPaused(false);
    }, CAPTURE_PAUSE);
    const isNew = !discovered.includes(item.slug);
    setAcquisition({ item, before, isNew });
    if (!isNew) return;
    const next = [...discovered, item.slug];
    setDiscovered(next);
    try {
      window.localStorage.setItem(LOGBOOK_KEY, JSON.stringify(next));
    } catch { /* The logbook still works for the current visit. */ }
  }

  useEffect(() => {
    function finishRange(event: globalThis.PointerEvent) {
      if (rangeGesture.current?.id === event.pointerId) rangeGesture.current = null;
    }
    window.addEventListener("pointerup", finishRange);
    window.addEventListener("pointercancel", finishRange);
    return () => {
      if (pauseTimer.current !== null) window.clearTimeout(pauseTimer.current);
      window.removeEventListener("pointerup", finishRange);
      window.removeEventListener("pointercancel", finishRange);
    };
  }, []);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setTime((current) => current < timeBounds.end ? Math.min(timeBounds.end, current + HOUR) : timeBounds.start);
    }, 600);
    return () => window.clearInterval(timer);
  }, [playing, timeBounds]);

  function setAngles(nextRA: number, nextDec: number, raTravel?: number) {
    if (pauseTimer.current !== null || (nextRA === ra && nextDec === dec && !raTravel)) return;
    const scan = scanPath({ ra, dec }, nextRA, nextDec, targets, lockedTarget, raTravel);
    if (scan.hit) {
      captureTarget(scan.hit, scan.before);
      return;
    }
    setAcquisition(null);
    if (!scan.locked) {
      setLockedTarget(null);
      setTarget(null);
    }
    setRA(nextRA);
    setDec(nextDec);
  }

  function selectTarget(item: Target) {
    if (pauseTimer.current !== null) return;
    pointer.current = null;
    setLockedTarget(item);
    setAcquisition(null);
    setTarget(item.slug);
    setRA(item.ra);
    setDec(item.dec);
    changeTime(Date.parse(item.time));
    setMjdDraft(null);
  }

  function changeTime(next: number) {
    if (!Number.isFinite(next)) return;
    const bounded = clamp(next, LIMIT_START, LIMIT_END);
    setTime(bounded);
    setTimeBounds((range) => bounded >= range.start && bounded <= range.end ? range : ({
      start: Math.max(LIMIT_START, Math.min(range.start, bounded - DAY)),
      end: Math.min(LIMIT_END, Math.max(range.end, bounded + DAY)),
    }));
    setPlaying(false);
  }

  function startDrag(event: PointerEvent<HTMLCanvasElement>) {
    if (pauseTimer.current !== null || !event.isPrimary || event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY, ra, dec, lastX: event.clientX };
  }

  function moveDrag(event: PointerEvent<HTMLCanvasElement>) {
    const start = pointer.current;
    if (start?.id !== event.pointerId) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    const raTravel = (event.clientX - start.lastX) * .6;
    start.lastX = event.clientX;
    setAngles(Number(wrap(start.ra + dx * .6).toFixed(4)) % 360, Number(clamp(start.dec - dy * .45, -90, 90).toFixed(4)), raTravel);
  }

  const rangeGuard: React.ComponentProps<"input"> = {
    "aria-disabled": aimPaused,
    onPointerDown(event) {
      if (pauseTimer.current !== null) event.preventDefault();
      else rangeGesture.current = { id: event.pointerId, interrupted: false };
    },
    onKeyDown(event) {
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"].includes(event.key)
        && (pauseTimer.current !== null || (event.repeat && acquisition))) event.preventDefault();
    },
  };

  const iso = new Date(time).toISOString();
  const query = new URLSearchParams({
    ra_deg: String(Number(ra.toFixed(6)) % 360),
    dec_deg: String(Number(dec.toFixed(6))),
  });

  return (
    <>
      <div className="orbital-header shell">
        <div className="orbital-targets" data-tour="obs-alvos" role="group" aria-label="Alvos de exemplo">
          {targets.map((item, index) => (
            <button className="orbital-target" key={item.slug} type="button" aria-pressed={target === item.slug}
              aria-disabled={aimPaused} onClick={() => selectTarget(item)}>
              <span className={`orbital-symbol target-${index % 3}`} aria-hidden="true" />
              {item.name}
              {discovered.includes(item.slug) && <span className="orbital-found-mark" aria-label="Descoberto">✓</span>}
            </button>
          ))}
          <button className="orbital-target" type="button" aria-pressed={target === null} aria-disabled={aimPaused} onClick={() => {
            if (pauseTimer.current !== null) return;
            setAcquisition(null);
            setTarget(null);
          }}>
            <span className="orbital-symbol manual" aria-hidden="true" /> Manual
          </button>
        </div>
      </div>

      <section className="orbital-stage" aria-label="Cena didática de apontamento" data-aim-paused={aimPaused}>
        <SceneCanvas ra={ra} dec={dec} time={time} variant="orbital" role="img" aria-label="Terra à esquerda e telescópio no centro com linha de visão"
          onPointerDown={startDrag} onPointerMove={moveDrag}
          onLostPointerCapture={() => { pointer.current = null; }} />
        <div className="orbital-ra" data-tour="obs-ra" data-adjusted={raAdjusted}>
          <div className="orbital-value"><label htmlFor="orbital-ra">Ascensão reta</label><output htmlFor="orbital-ra">{angleLabel.format(ra)}°</output></div>
          <input id="orbital-ra" type="range" min={0} max={359.9} step={.1} value={ra} {...rangeGuard}
            onChange={(event) => { if (!rangeGesture.current?.interrupted) setAngles(event.currentTarget.valueAsNumber, dec); }} />
          <div className="orbital-scale" aria-hidden="true"><span>0°</span><span>360°</span></div>
          {raAdjusted && <small className="orbital-adjusted">RA ajustada automaticamente</small>}
        </div>
        <p className="orbital-scope-label">SPHEREx <span>· modelo didático</span></p>
        {acquisition && <span key={acquisition.item.slug} className="orbital-discovery-pulse" aria-hidden="true" />}
        <div className="orbital-dec" data-tour="obs-dec" data-adjusted={decAdjusted}>
          <div className="orbital-value"><label htmlFor="orbital-dec">Inclinação · Dec</label><output htmlFor="orbital-dec">{angleLabel.format(dec)}°</output></div>
          <input id="orbital-dec" type="range" min={-90} max={90} step={.1} value={dec} {...rangeGuard}
            onChange={(event) => { if (!rangeGesture.current?.interrupted) setAngles(ra, event.currentTarget.valueAsNumber); }} />
          <div className="orbital-scale" aria-hidden="true"><span>−90°</span><span>0°</span><span>+90°</span></div>
          {decAdjusted && <small className="orbital-adjusted">Dec ajustada automaticamente</small>}
          <Link className="button primary" href={`/explorar/?${query}`}>Importar para o explorador</Link>
        </div>
        {/* Clicar no card aberto mostra a ficha do astro; o botão interno garante acesso por teclado. */}
        <aside className="orbital-logbook" data-tour="obs-diario" aria-label="Diário de bordo" data-aligned={Boolean(acquisition)}
          data-clickable={Boolean(acquisition && targetInfo[acquisition.item.slug])}
          onClick={() => { if (acquisition && targetInfo[acquisition.item.slug]) setSheet(acquisition.item); }}>
          <div className="orbital-logbook-title"><strong>Diário de bordo</strong><span>{discovered.length} de {targets.length} descobertos</span></div>
          <div className="orbital-discovery-message" role="status">
            {acquisition && <>
              <p className="orbital-acquisition-name"><strong>{acquisition.isNew ? "Descoberta registrada" : "Alvo reencontrado"}:</strong> {acquisition.item.name}</p>
              <p>{raAdjusted || decAdjusted ? "Mira ajustada às coordenadas exatas." : "A mira já estava nas coordenadas exatas."}</p>
              {(raAdjusted || decAdjusted) && <ul className="orbital-correction">
                {raAdjusted && <li>RA <span>{exactAngle.format(acquisition.before.ra)}° → {exactAngle.format(acquisition.item.ra)}°</span></li>}
                {decAdjusted && <li>Dec <span>{exactAngle.format(acquisition.before.dec)}° → {exactAngle.format(acquisition.item.dec)}°</span></li>}
              </ul>}
            </>}
          </div>
          {acquisition && <p className="orbital-pause-note" role="status">{aimPaused ? "Mira travada por um instante." : "Mira liberada. Continue explorando."}</p>}
          {acquisition && targetInfo[acquisition.item.slug] && (
            <button type="button" className="orbital-sheet-link" aria-haspopup="dialog">
              Conhecer a história de {acquisition.item.name} <span aria-hidden="true">›</span>
            </button>
          )}
          {!acquisition && <>
            <div className="orbital-signal">
              <div className="orbital-signal-label">
                <span>Faixa de descoberta: 0° a {CAPTURE_RADIUS}° do alvo</span>
                {signal && <strong>Sinal a {angleLabel.format(signal.distance)}°</strong>}
              </div>
              {signal && <div className="orbital-signal-track" aria-hidden="true">
                <span className="orbital-signal-zone" style={{ width: `${CAPTURE_RADIUS / SIGNAL_SCALE * 100}%` }} />
                <span className="orbital-signal-marker" style={{ left: `clamp(5px, ${Math.min(signal.distance / SIGNAL_SCALE, 1) * 100}%, 100% - 5px)` }} />
              </div>}
            </div>
            <p>{signal ? <>{axisHint("RA", signal.item.ra - ra)} · {axisHint("Dec", signal.item.dec - dec)}</>
              : discovered.length === targets.length ? "Mapa completo. Você encontrou todos os alvos!"
              : "Afaste a mira e volte para registrar esse alvo."}</p>
          </>}
        </aside>
      </section>

      <section className="orbital-time" data-tour="obs-tempo" aria-labelledby="orbital-time-label">
        <h2 id="orbital-time-label">Tempo</h2>
        <div className="orbital-time-modes" role="group" aria-label="Formato do tempo">
          <button type="button" aria-pressed={mode === "utc"} onClick={() => { setMjdDraft(null); setMode("utc"); }}>Data e hora UTC</button>
          <button type="button" aria-pressed={mode === "mjd"} onClick={() => setMode("mjd")}>MJD</button>
        </div>
        <div className="orbital-datetime">
          {mode === "utc" ? <>
            <input type="date" aria-label="Data UTC" min="1900-01-01" max="2100-12-31" value={iso.slice(0, 10)}
              onChange={(event) => changeTime(Date.parse(`${event.currentTarget.value}T${iso.slice(11, 23)}Z`))} />
            <input type="time" aria-label="Hora UTC" step={1} value={iso.slice(11, 19)}
              onChange={(event) => changeTime(Date.parse(`${iso.slice(0, 10)}T${event.currentTarget.value}Z`))} />
          </> : <input className="orbital-mjd" type="text" inputMode="decimal" aria-label="Data Juliana Modificada"
              value={mjdDraft ?? (time / DAY + MJD_AT_UNIX).toFixed(6)}
              onBlur={() => setMjdDraft(null)}
              onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }}
              onChange={(event) => {
                const raw = event.currentTarget.value;
                setMjdDraft(raw);
                setPlaying(false);
                if (/^\d{5}(?:[.,]\d+)?$/.test(raw)) changeTime(Math.round((Number(raw.replace(",", ".")) - MJD_AT_UNIX) * DAY));
              }} />}
        </div>
        <div className="orbital-transport">
          <button type="button" aria-label="Voltar um dia" onClick={() => changeTime(time - DAY)}><span aria-hidden="true">‹</span></button>
          <button type="button" className="orbital-play" aria-label={playing ? "Pausar tempo" : "Reproduzir tempo"}
            onClick={() => { setMjdDraft(null); setPlaying(!playing); }}>
            <span className={playing ? "orbital-pause-icon" : "orbital-play-icon"} aria-hidden="true" />
          </button>
          <input type="range" aria-label="Percorrer tempo da simulação" min={timeBounds.start} max={timeBounds.end}
            step="any" value={time} aria-valuetext={iso}
            onChange={(event) => changeTime(Math.round(event.currentTarget.valueAsNumber))} />
          <button type="button" aria-label="Avançar um dia" onClick={() => changeTime(time + DAY)}><span aria-hidden="true">›</span></button>
        </div>
      </section>
      <TargetSheet target={sheet} onClose={() => setSheet(null)} />
      <footer className="orbital-credit">
        <span>Simulação de apontamento e rotação, sem telemetria orbital.</span>
        <a href="https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/">Textura NASA Earth Observatory / Blue Marble</a>
      </footer>
    </>
  );
}
