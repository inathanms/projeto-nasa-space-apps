"use client";

import { useLocale } from "../ui/LocaleProvider";
import { forLocales } from "../../lib/i18n";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRef, useState, type PointerEvent } from "react";
import { parseCoordinate } from "../../lib/coordinates";
import SceneLoading from "../ui/SceneLoading";

const SceneCanvas = dynamic(() => import("../ui/SceneCanvas"), { ssr: false, loading: SceneLoading });

type Angles = { ra: number; dec: number };
type Target = Angles & { name: string };
const INITIAL: Angles = { ra: 35, dec: 28 };
const clampDec = (value: number) => Math.max(-90, Math.min(90, value));
const wrapRA = (value: number) => value >= 0 && value < 360 ? value : ((value % 360) + 360) % 360;
const anglesByLocale = forLocales((language) => new Intl.NumberFormat(language, { maximumFractionDigits: 6 }));

function AngleInput({ name, value, change }: {
  name: "RA" | "Dec"; value: number; change: (value: number) => void;
}) {
  const { t, locale } = useLocale();
  const angle = anglesByLocale[locale];
  const [draft, setDraft] = useState<string | null>(null);
  const ascension = name === "RA";
  const label = ascension ? t("Ascensão reta") : t("Declinação");
  const coordinate = draft === null ? value : parseCoordinate(draft);
  const invalid = draft !== null && !Number.isFinite(coordinate);
  const description = `angle-${name}-format`;
  const feedback = `angle-${name}-feedback`;
  function update(raw: string) {
    setDraft(raw);
    const coordinate = parseCoordinate(raw);
    if (Number.isFinite(coordinate)) change(coordinate);
  }
  return (
    <div className="pointing-angle">
      <div className="pointing-angle-label">
        <label htmlFor={`angle-${name}`}><strong>{name}</strong> {label}</label>
        <span className="pointing-number">
          <input id={`angle-${name}`} inputMode="decimal" value={draft ?? value}
            aria-describedby={invalid ? `${description} ${feedback}` : description} aria-invalid={invalid}
            onChange={(event) => update(event.target.value)} onBlur={() => { if (!invalid) setDraft(null); }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setDraft(null);
              if (event.key === "Enter" && !invalid) event.currentTarget.blur();
            }} />
          <span aria-hidden="true">°</span>
        </span>
      </div>
      <input type="range" aria-label={t("Ajustar {label}", { label: label.toLowerCase() })}
        min={ascension ? 0 : -90} max={ascension ? 359.9 : 90}
        step="0.1" value={value} aria-valuetext={t("{value} graus", { value: angle.format(value) })}
        onChange={(event) => { setDraft(null); change(event.target.valueAsNumber); }} />
      <div className="pointing-limits" aria-hidden="true"><span>{ascension ? "0°" : "−90°"}</span><span>{ascension ? "360°" : "+90°"}</span></div>
      <p id={description} className="sr-only">
        {t("Em graus decimais.")} {ascension ? t("A ascensão reta dá a volta em 360 graus.") : t("A declinação é limitada a menos 90 e mais 90 graus.")}
      </p>
      <p id={feedback} className="error pointing-feedback" role="status">{invalid ? t("Digite um número em graus, por exemplo 35,5.") : ""}</p>
    </div>
  );
}

export default function PointingLab({ targets }: { targets: Target[] }) {
  const { t, href } = useLocale();
  const [angles, setAngles] = useState(INITIAL);
  const [resetCount, setResetCount] = useState(0);
  const [dragging, setDragging] = useState(false);
  const pointer = useRef<{ id: number; x: number; y: number } | null>(null);

  function startDrag(event: PointerEvent<HTMLCanvasElement>) {
    if (!event.isPrimary || event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
    setDragging(true);
  }

  function moveDrag(event: PointerEvent<HTMLCanvasElement>) {
    const previous = pointer.current;
    if (previous?.id !== event.pointerId) return;
    const dx = event.clientX - previous.x;
    const dy = event.clientY - previous.y;
    pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
    setAngles(({ ra, dec }) => ({
      ra: Number(wrapRA(ra + dx * 0.65).toFixed(4)) % 360,
      dec: Number(clampDec(dec - dy * 0.5).toFixed(4)),
    }));
  }

  function stopDrag(event: PointerEvent<HTMLCanvasElement>) {
    if (pointer.current?.id !== event.pointerId) return;
    pointer.current = null;
    setDragging(false);
  }

  function selectAngles(next: Angles) {
    setAngles(next);
    setResetCount((previous) => previous + 1);
  }

  const query = new URLSearchParams({
    ra_deg: String(Number(angles.ra.toFixed(6)) % 360),
    dec_deg: String(Number(angles.dec.toFixed(6))),
  });
  return (
    <div className="pointing-grid">
      <figure className="pointing-figure">
        <SceneCanvas ra={angles.ra} dec={angles.dec} role="img" aria-label={t("Globo terrestre com eixo polar, equador e linha de visão do telescópio")}
          aria-describedby="pointing-description"
          className={dragging ? "pointing-canvas dragging" : "pointing-canvas"}
          onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={stopDrag}
          onPointerCancel={stopDrag} onLostPointerCapture={stopDrag} />
        <figcaption className="pointing-caption">
          <span className="pointing-legend ra">{t("Ascensão reta")}</span>
          <span className="pointing-legend dec">{t("Declinação")}</span>
          <span className="pointing-legend sight">{t("Linha de visão")}</span>
        </figcaption>
      </figure>
      <section className="pointing-controls" aria-labelledby="pointing-controls-title">
        <h2 id="pointing-controls-title">{t("Coordenadas celestes")}</h2>
        <p className="muted" id="pointing-description">{t("Digite as coordenadas em graus decimais ou use as setas nos controles deslizantes. No globo, arraste na horizontal para mudar a RA e na vertical para mudar a declinação.")}</p>
        <AngleInput key={`ra-${resetCount}`} name="RA" value={angles.ra} change={(ra) => setAngles((previous) => ({ ...previous, ra: wrapRA(ra) }))} />
        <AngleInput key={`dec-${resetCount}`} name="Dec" value={angles.dec} change={(dec) => setAngles((previous) => ({ ...previous, dec: clampDec(dec) }))} />
        {targets.length > 0 && <label className="pointing-target">
          {t("Campos de exemplo")}
          <select value={targets.find((target) => target.ra === angles.ra && target.dec === angles.dec)?.name ?? ""}
            onChange={(event) => {
              const target = targets.find((item) => item.name === event.target.value);
              if (target) selectAngles({ ra: target.ra, dec: target.dec });
            }}>
            <option value="" disabled>{t("Escolher um campo")}</option>
            {targets.map((target) => <option key={target.name} value={target.name}>{target.name}</option>)}
          </select>
        </label>}
        <div className="pointing-actions">
          <Link className="button primary" href={href(`/explorar/?${query}`)}>{t("Usar no explorador")}</Link>
          <button className="button secondary" type="button" onClick={() => selectAngles(INITIAL)}>{t("Restaurar")}</button>
        </div>
        <p className="pointing-note">{t("Modelo didático com a Terra como referência. A linha representa uma direção no céu e o telescópio é esquemático.")}</p>
        <p className="pointing-credit">{t("Textura da Terra ·")} <a href="https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/">NASA Earth Observatory / Blue Marble</a></p>
      </section>
    </div>
  );
}
