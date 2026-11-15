"use client";

import { useLocale } from "../ui/LocaleProvider";
import { forLocales } from "../../lib/i18n";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useEffectEvent, useRef, useState, type PointerEvent } from "react";
import { axisHint, CAPTURE_RADIUS, clamp, nearestTarget, scanPath, wrap, type Target } from "../../lib/pointing";
import SceneLoading from "../ui/SceneLoading";
import TargetSheet from "./target-sheet";
import { setDiscoveryField } from "../../lib/discovery";

const SceneCanvas = dynamic(() => import("../ui/SceneCanvas"), { ssr: false, loading: SceneLoading });

const DAY = 86_400_000;
const HOUR = 3_600_000;
const PLAYBACK_STEPS = 120;
const PLAYBACK_RA_STEP = 360 / PLAYBACK_STEPS;
const MJD_AT_UNIX = 40587;
const REFERENCE = Date.parse("2025-04-27T16:58:48.188Z");
const LIMIT_START = Date.parse("1900-01-01T00:00:00Z");
const LIMIT_END = Date.parse("2100-12-31T23:59:59Z");
const SIGNAL_SCALE = CAPTURE_RADIUS * 3;
const DISCOVERY_HOLD_MS = 2000;
const LOGBOOK_KEY = "spherex:observatory:discoveries:v1";
const angleLabels = forLocales((language) => new Intl.NumberFormat(language, { maximumFractionDigits: 2 }));
const exactAngles = forLocales((language) => new Intl.NumberFormat(language, { maximumFractionDigits: 6 }));

export default function Observatory({ targets }: { targets: Target[] }) {
  const { t, locale, href } = useLocale();
  const angleLabel = angleLabels[locale];
  const exactAngle = exactAngles[locale];
  const [lockedTarget, setLockedTarget] = useState<Target | null>(null);
  const [discovered, setDiscovered] = useState<string[]>([]);
  const [lastDiscovery, setLastDiscovery] = useState<Target | null>(null);
  const [holdingAim, setHoldingAim] = useState(false);
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
  const [sheet, setSheet] = useState<{ target: Target; focusOnOpen: boolean } | null>(null);

  // Informa ao widget de descoberta para onde a mira aponta e em que instante.
  useEffect(() => {
    setDiscoveryField({ name: lockedTarget?.name, ra, dec, times: [new Date(time).toISOString()] });
  }, [ra, dec, time, lockedTarget]);
  useEffect(() => () => setDiscoveryField(null), []);
  const pointer = useRef<{ id: number; x: number; y: number } | null>(null);
  const holdUntil = useRef(0);
  const holdTimer = useRef<number | undefined>(undefined);
  const sheetTrigger = useRef<HTMLButtonElement>(null);
  const discoveredCount = targets.filter((item) => discovered.includes(item.slug)).length;
  const signal = nearestTarget(ra, dec, targets, (item) => discovered.includes(item.slug) || item.slug === lockedTarget?.slug);
  const mjdValue = mjdDraft === null ? NaN : Number(mjdDraft.trim().replace(",", "."));
  const mjdTime = Math.round((mjdValue - MJD_AT_UNIX) * DAY);
  const mjdInvalid = mjdDraft !== null && (!/^\d{5}(?:[.,]\d+)?$/.test(mjdDraft.trim()) ||
    !Number.isFinite(mjdTime) || mjdTime < LIMIT_START || mjdTime > LIMIT_END);

  useEffect(() => {
    try {
      const stored: unknown = JSON.parse(window.localStorage.getItem(LOGBOOK_KEY) ?? "[]");
      if (Array.isArray(stored)) {
        const slugs = stored.filter((item): item is string => typeof item === "string");
        setDiscovered([...new Set(slugs.map((slug) => slug === "m101" ? "preset-m101" : slug))]);
      }
    } catch { /* The logbook still works for the current visit. */ }
  }, [targets]);

  useEffect(() => () => window.clearTimeout(holdTimer.current), []);

  function recordDiscovery(item: Target) {
    holdUntil.current = performance.now() + DISCOVERY_HOLD_MS;
    window.clearTimeout(holdTimer.current);
    setHoldingAim(true);
    holdTimer.current = window.setTimeout(() => setHoldingAim(false), DISCOVERY_HOLD_MS);
    setLockedTarget(item);
    setRA(item.ra);
    setDec(item.dec);
    setLastDiscovery(item);
    setSheet({ target: item, focusOnOpen: false });
    const next = [...discovered, item.slug];
    setDiscovered(next);
    try {
      window.localStorage.setItem(LOGBOOK_KEY, JSON.stringify(next));
    } catch { /* The logbook still works for the current visit. */ }
  }

  const advancePlayback = useEffectEvent((timeStep: number) => {
    setTime((current) => current < timeBounds.end ? Math.min(timeBounds.end, current + timeStep) : timeBounds.start);
    setAngles(wrap(ra + PLAYBACK_RA_STEP), dec, PLAYBACK_RA_STEP, "playback");
  });

  useEffect(() => {
    if (!playing) return;
    const timeStep = Math.max(HOUR, Math.round((timeBounds.end - timeBounds.start) / PLAYBACK_STEPS));
    const timer = window.setInterval(() => advancePlayback(timeStep), 600);
    return () => window.clearInterval(timer);
  }, [playing, timeBounds]);

  function setAngles(nextRA: number, nextDec: number, raTravel?: number, mode: "manual" | "playback" = "manual") {
    if (performance.now() < holdUntil.current) return;
    if (nextRA === ra && nextDec === dec && !raTravel) return;
    if (mode === "manual") setPlaying(false);
    const candidates = mode === "manual" ? targets.filter((item) => !discovered.includes(item.slug)) : [];
    const scan = scanPath({ ra, dec }, nextRA, nextDec, candidates, lockedTarget, raTravel);
    if (scan.hit) {
      recordDiscovery(scan.hit);
      return;
    }
    if (!scan.locked) setLockedTarget(null);
    setRA(nextRA);
    setDec(nextDec);
  }

  function selectTarget(item: Target) {
    if (performance.now() < holdUntil.current) return;
    pointer.current = null;
    setLockedTarget(item);
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
    if (!event.isPrimary || event.button !== 0) return;
    setPlaying(false);
    event.currentTarget.setPointerCapture(event.pointerId);
    pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
  }

  function moveDrag(event: PointerEvent<HTMLCanvasElement>) {
    const start = pointer.current;
    if (start?.id !== event.pointerId) return;
    const raTravel = (event.clientX - start.x) * .6;
    const decTravel = (start.y - event.clientY) * .45;
    start.x = event.clientX;
    start.y = event.clientY;
    setAngles(Number(wrap(ra + raTravel).toFixed(4)) % 360, Number(clamp(dec + decTravel, -90, 90).toFixed(4)), raTravel);
  }

  const iso = new Date(time).toISOString();
  const query = new URLSearchParams({
    ra_deg: String(Number(ra.toFixed(6)) % 360),
    dec_deg: String(Number(dec.toFixed(6))),
  });
  if (lockedTarget && ra === lockedTarget.ra && dec === lockedTarget.dec) {
    query.set("exemplo", lockedTarget.slug);
  } else {
    query.set("modo", "consultar");
  }

  return (
    <>
      <div className="orbital-header shell">
        <label className="orbital-targets" data-tour="obs-alvos" htmlFor="orbital-target">{t("Campo de observação")}
          <select id="orbital-target" className="control-field" value={lockedTarget?.slug ?? ""} onChange={(event) => {
            const item = targets.find(({ slug }) => slug === event.currentTarget.value);
            if (item) selectTarget(item);
            else setLockedTarget(null);
          }}>
            <option value="">Manual</option>
            <optgroup label={t("Alvos pré-configurados do SPHEREx")}>
              {targets.map((item) => <option key={item.slug} value={item.slug}>
                {item.name}{discovered.includes(item.slug) ? ` · ${t("Descoberto")}` : ""}
              </option>)}
            </optgroup>
          </select>
        </label>
      </div>

      <div className="shell orbital-workspace">
        <section className="orbital-time" data-tour="obs-tempo" aria-labelledby="orbital-time-label">
          <h2 id="orbital-time-label">{t("Tempo")}</h2>
          <div className="orbital-time-modes" role="group" aria-label={t("Formato do tempo")}>
            <button type="button" aria-pressed={mode === "utc"} onClick={() => { setMjdDraft(null); setMode("utc"); }}>{t("Data e hora UTC")}</button>
            <button type="button" aria-pressed={mode === "mjd"} onClick={() => setMode("mjd")}>MJD</button>
          </div>
          <div className="orbital-datetime">
            {mode === "utc" ? <>
              <input type="date" aria-label={t("Data UTC")} min="1900-01-01" max="2100-12-31" value={iso.slice(0, 10)}
                onChange={(event) => changeTime(Date.parse(`${event.currentTarget.value}T${iso.slice(11, 23)}Z`))} />
              <input type="time" aria-label={t("Hora UTC")} step={1} value={iso.slice(11, 19)}
                onChange={(event) => changeTime(Date.parse(`${iso.slice(0, 10)}T${event.currentTarget.value}Z`))} />
            </> : <input className="orbital-mjd" type="text" inputMode="decimal" aria-label={t("Data Juliana Modificada")}
                aria-invalid={mjdInvalid} aria-describedby={mjdInvalid ? "orbital-mjd-error" : undefined}
                value={mjdDraft ?? (time / DAY + MJD_AT_UNIX).toFixed(6)}
                onBlur={() => setMjdDraft(null)}
                onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }}
                onChange={(event) => {
                  const raw = event.currentTarget.value.trim();
                  setMjdDraft(raw);
                  setPlaying(false);
                  const next = Math.round((Number(raw.replace(",", ".")) - MJD_AT_UNIX) * DAY);
                  if (/^\d{5}(?:[.,]\d+)?$/.test(raw) && next >= LIMIT_START && next <= LIMIT_END) changeTime(next);
                }} />}
          </div>
          <div className="orbital-transport">
            <button type="button" aria-label={t("Voltar um dia")} onClick={() => changeTime(time - DAY)}><span className="orbital-day-arrow back" aria-hidden="true" /></button>
            <button type="button" className="orbital-play" aria-label={playing ? t("Pausar tempo") : t("Reproduzir tempo")}
              onClick={() => { setMjdDraft(null); setPlaying((current) => !current); }}>
              <span className={playing ? "orbital-pause-icon" : "orbital-play-icon"} aria-hidden="true" />
            </button>
            <input type="range" aria-label={t("Percorrer tempo da simulação")} min={timeBounds.start} max={timeBounds.end}
              step="any" value={time} aria-valuetext={iso}
              onChange={(event) => changeTime(Math.round(event.currentTarget.valueAsNumber))} />
            <button type="button" aria-label={t("Avançar um dia")} onClick={() => changeTime(time + DAY)}><span className="orbital-day-arrow" aria-hidden="true" /></button>
          </div>
          <p className="error orbital-mjd-error" id="orbital-mjd-error" role="status">
            {mjdInvalid ? t("Informe uma data MJD com cinco dígitos e decimais opcionais, entre os anos 1900 e 2100.") : ""}
          </p>
        </section>
        <div className="orbital-pointing">
          <div className="orbital-ra" data-tour="obs-ra">
            <div className="orbital-value"><label htmlFor="orbital-ra">{t("Ascensão reta")}</label><span aria-hidden="true">{angleLabel.format(ra)}°</span></div>
            <input id="orbital-ra" type="range" min={0} max={359.9} step={.1} value={ra} aria-valuetext={t("{value} graus", { value: exactAngle.format(ra) })}
              onChange={(event) => {
                const next = event.currentTarget.valueAsNumber;
                if (next !== clamp(Math.round(ra * 10) / 10, 0, 359.9)) setAngles(next, dec);
              }} />
            <div className="orbital-scale" aria-hidden="true"><span>0°</span><span>360°</span></div>
          </div>
          <div className="orbital-dec" data-tour="obs-dec">
            <div className="orbital-value"><label htmlFor="orbital-dec">{t("Declinação · Dec")}</label><span aria-hidden="true">{angleLabel.format(dec)}°</span></div>
            <input id="orbital-dec" type="range" min={-90} max={90} step={.1} value={dec} aria-valuetext={t("{value} graus", { value: exactAngle.format(dec) })}
              onChange={(event) => {
                const next = event.currentTarget.valueAsNumber;
                if (next !== Math.round(dec * 10) / 10) setAngles(ra, next);
              }} />
            <div className="orbital-scale" aria-hidden="true"><span>−90°</span><span>0°</span><span>+90°</span></div>
            <Link className="button primary" href={href(`/explorar/?${query}`)}>{t("Importar para o explorador")}</Link>
          </div>
        </div>
        <section className="orbital-stage" aria-label={t("Cena didática de apontamento")} aria-describedby="orbital-guide">
          <p className="sr-only" id="orbital-guide">{t("Use os controles de ascensão reta e declinação para mover a mira. O diário de bordo indica a direção de um alvo próximo e anuncia as descobertas.")}</p>
          <SceneCanvas ra={ra} dec={dec} time={time} variant="orbital" role="img" aria-label={t("Terra à esquerda e telescópio no centro com linha de visão")}
            onPointerDown={startDrag} onPointerMove={moveDrag}
            onLostPointerCapture={() => { pointer.current = null; }} />
          <p className="orbital-scope-label">SPHEREx <span>{t("· modelo didático")}</span></p>
          {lastDiscovery && <span key={lastDiscovery.slug} className="orbital-discovery-pulse" aria-hidden="true" />}
        </section>
        <div className="orbital-sidebar">
          {/* Clicar no card aberto mostra a ficha do astro; o botão interno garante acesso por teclado. */}
          <aside className="orbital-logbook" data-tour="obs-diario" aria-label={t("Diário de bordo")} data-aligned={Boolean(lastDiscovery)}
            data-clickable={Boolean(lastDiscovery)}
            onClick={() => {
              if (lastDiscovery) setSheet({ target: lastDiscovery, focusOnOpen: true });
            }}>
            <div className="orbital-logbook-title"><strong>{t("Diário de bordo")}</strong><span>{t("{count} de {total} descobertos", { count: discoveredCount, total: targets.length })}</span></div>
            <div className="orbital-discovery-message" role="status">
              {lastDiscovery && <p className="orbital-acquisition-name">
                <strong>{t("Descoberta registrada")}:</strong> {lastDiscovery.name}
              </p>}
              {holdingAim && <p>{t("Mira fixada no astro por 2 segundos.")}</p>}
            </div>
            {lastDiscovery && (
              <button ref={sheetTrigger} type="button" className="orbital-sheet-link"
                  aria-expanded={sheet?.target.slug === lastDiscovery.slug} aria-controls={sheet ? "target-sheet" : undefined}>
                {t("Ver ficha de {name}", { name: lastDiscovery.name })} <span aria-hidden="true">›</span>
              </button>
            )}
            <div className="orbital-signal">
              <div className="orbital-signal-label">
                <span>{t("Faixa de descoberta: 0° a {radius}° do alvo", { radius: CAPTURE_RADIUS })}</span>
                {signal && <strong>{t("Sinal a {distance}°", { distance: angleLabel.format(signal.distance) })}</strong>}
              </div>
              {signal && <div className="orbital-signal-track" aria-hidden="true">
                <span className="orbital-signal-zone" style={{ width: `${CAPTURE_RADIUS / SIGNAL_SCALE * 100}%` }} />
                <span className="orbital-signal-marker" style={{ left: `clamp(5px, ${Math.min(signal.distance / SIGNAL_SCALE, 1) * 100}%, 100% - 5px)` }} />
              </div>}
            </div>
            <p>{signal ? <>{axisHint("RA", signal.item.ra - ra, locale)} · {axisHint("Dec", signal.item.dec - dec, locale)}</>
              : discoveredCount === targets.length ? t("Mapa completo. Você encontrou todos os alvos!")
              : t("Afaste a mira e volte para registrar esse alvo.")}</p>
          </aside>
          <TargetSheet target={sheet?.target ?? null} focusOnOpen={sheet?.focusOnOpen ?? false} onClose={() => {
            setSheet(null);
            sheetTrigger.current?.focus();
          }} />
        </div>
      </div>
      <footer className="orbital-credit">
        <span>{t("Simulação de apontamento e rotação, sem telemetria orbital.")}</span>
        <a href="https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/">{t("Textura NASA Earth Observatory / Blue Marble")}</a>
      </footer>
    </>
  );
}
