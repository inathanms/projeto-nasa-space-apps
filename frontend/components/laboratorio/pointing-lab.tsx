"use client";

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

function AngleInput({ name, value, change }: {
  name: "RA" | "Dec"; value: number; change: (value: number) => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const ascension = name === "RA";
  const label = ascension ? "Ascensão reta" : "Declinação";
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
            onChange={(event) => update(event.target.value)} onBlur={() => setDraft(null)}
            onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }} />
          <span aria-hidden="true">°</span>
        </span>
      </div>
      <input type="range" aria-label={`Ajustar ${label.toLowerCase()}`}
        min={ascension ? 0 : -90} max={ascension ? 359.9 : 90}
        step="0.1" value={value} onChange={(event) => change(event.target.valueAsNumber)} />
      <div className="pointing-limits" aria-hidden="true"><span>{ascension ? "0°" : "−90°"}</span><span>{ascension ? "360°" : "+90°"}</span></div>
    </div>
  );
}

export default function PointingLab({ targets }: { targets: Target[] }) {
  const [angles, setAngles] = useState(INITIAL);
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

  const query = new URLSearchParams({
    ra_deg: String(Number(angles.ra.toFixed(6)) % 360),
    dec_deg: String(Number(angles.dec.toFixed(6))),
  });
  return (
    <div className="pointing-grid">
      <figure className="pointing-figure">
        <SceneCanvas ra={angles.ra} dec={angles.dec} role="img" aria-label="Globo terrestre com eixo polar, equador e linha de visão do telescópio"
          className={dragging ? "pointing-canvas dragging" : "pointing-canvas"}
          onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={stopDrag}
          onPointerCancel={stopDrag} onLostPointerCapture={stopDrag} />
        <figcaption className="pointing-caption">
          <span className="pointing-legend ra">Ascensão reta</span>
          <span className="pointing-legend dec">Declinação</span>
          <span className="pointing-legend sight">Linha de visão</span>
        </figcaption>
      </figure>
      <section className="pointing-controls" aria-labelledby="pointing-controls-title">
        <h2 id="pointing-controls-title">Coordenadas celestes</h2>
        <p className="muted">Arraste na horizontal para mudar a RA e na vertical para mudar a Dec. Os campos aceitam valores em graus decimais.</p>
        <AngleInput name="RA" value={angles.ra} change={(ra) => setAngles((previous) => ({ ...previous, ra: wrapRA(ra) }))} />
        <AngleInput name="Dec" value={angles.dec} change={(dec) => setAngles((previous) => ({ ...previous, dec: clampDec(dec) }))} />
        {targets.length > 0 && <label className="pointing-target">
          Campos de exemplo
          <select value={targets.find((target) => target.ra === angles.ra && target.dec === angles.dec)?.name ?? ""}
            onChange={(event) => {
              const target = targets.find((item) => item.name === event.target.value);
              if (target) setAngles({ ra: target.ra, dec: target.dec });
            }}>
            <option value="" disabled>Escolher um campo</option>
            {targets.map((target) => <option key={target.name} value={target.name}>{target.name}</option>)}
          </select>
        </label>}
        <div className="pointing-actions">
          <Link className="button primary" href={`/explorar/?${query}`}>Usar no explorador</Link>
          <button className="button secondary" type="button" onClick={() => setAngles(INITIAL)}>Restaurar</button>
        </div>
        <p className="pointing-note">Modelo didático com a Terra como referência. A linha representa uma direção no céu e o telescópio é esquemático.</p>
        <p className="pointing-credit">Textura da Terra · <a href="https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation/base-map/">NASA Earth Observatory / Blue Marble</a></p>
      </section>
    </div>
  );
}
