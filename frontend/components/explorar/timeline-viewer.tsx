"use client";

import Image from "next/image";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { formatDate, sourceLink, type Frame } from "../../lib/sequence";
import { observationIdForExposure, type CatalogExposure, type Timeline } from "../../lib/timeline";
import { apiErrorMessage, fetchExposure, isUnavailableExposure, shareCoverage, type RenderedExposure } from "../../lib/spherex-api";
import { useSkySwipe } from "./use-sky-swipe";

const timeUTC = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC",
});

export default function TimelineViewer({ timeline, api, savedFrames, onClose }: {
  timeline: Timeline; api?: string; savedFrames: Frame[]; onClose: () => void;
}) {
  const exposures = timeline.exposures;
  const { days, dayOptions, indexById, byDetector } = useMemo(() => {
    const days = new Map<string, CatalogExposure[]>();
    const indexById = new Map<string, number>();
    const byDetector = new Map<string, CatalogExposure[]>();

    exposures.forEach((exposure, index) => {
      indexById.set(exposure.image_id, index);
      const day = exposure.observed_at_utc.slice(0, 10);
      const dailyGroup = days.get(day);
      if (dailyGroup) dailyGroup.push(exposure);
      else days.set(day, [exposure]);

      const detectorGroup = byDetector.get(exposure.detector);
      if (detectorGroup) detectorGroup.push(exposure);
      else byDetector.set(exposure.detector, [exposure]);
    });

    const dayOptions = Array.from(days, ([day, items]) =>
      <option key={day} value={day}>{formatDate(items[0].observed_at_utc)} · {items.length} imagens</option>,
    );
    return { days, dayOptions, indexById, byDetector };
  }, [exposures]);
  const [{ selected, frame }, setCurrent] = useState<{ selected?: CatalogExposure; frame?: Frame }>(() => {
    const initial = exposures.find((item) => item.frame_id === savedFrames[0]?.frame_id);
    return { selected: initial ?? exposures[0], frame: initial ? savedFrames[0] : undefined };
  });
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [message, setMessage] = useState("");
  const [reference, setReference] = useState<string>();
  const sky = useRef<HTMLElement>(null);
  const cachedReference = useRef<{ id: string; image: RenderedExposure } | null>(null);
  const pending = useRef<AbortController | null>(null);
  const day = selected?.observed_at_utc.slice(0, 10) ?? "";
  const index = selected ? indexById.get(selected.image_id) ?? -1 : -1;
  const source = sourceLink(selected?.source_url ?? null);
  const cutout = sourceLink(selected?.cutout_url ?? null);
  const observationId = selected && observationIdForExposure(selected);
  const isLiveFrame = frame && frame.frame_id === observationId;
  const playable = selected && api && frame && byDetector.get(selected.detector)?.some(
    (item) => item.collection === selected.collection && item.observed_at_utc !== selected.observed_at_utc,
  );

  useEffect(() => () => pending.current?.abort(), []);

  function pause() {
    pending.current?.abort();
    pending.current = null;
    setPlaying(false);
    setBusy(false);
  }

  async function choose(item: CatalogExposure, reuseSaved = false, trigger?: HTMLButtonElement) {
    pause();
    setReference(undefined);
    cachedReference.current = null;
    setMessage("");
    const local = reuseSaved ? savedFrames.find((image) => image.frame_id === item.frame_id) : undefined;
    setCurrent({ selected: item, frame: local });
    if (local || !api || !observationIdForExposure(item)) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try {
      const image = await fetchExposure(api, timeline, item, controller.signal);
      if (!controller.signal.aborted) {
        cachedReference.current = { id: item.image_id, image };
        if (trigger && document.activeElement === trigger) sky.current?.focus();
        setCurrent({ selected: item, frame: image.frame });
      }
    } catch (error) {
      if (!controller.signal.aborted) setMessage(apiErrorMessage(error));
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setBusy(false);
      }
    }
  }

  async function play() {
    if (!api || !selected || !playable || busy || pending.current) return;
    const anchorIndex = reference ? indexById.get(reference) : undefined;
    const anchor = anchorIndex === undefined ? selected : exposures[anchorIndex];
    if (!observationIdForExposure(anchor)) return;
    const pool = byDetector.get(anchor.detector) ?? [];
    const controller = new AbortController();
    pending.current = controller;
    setPlaying(true);
    setBusy(true);
    setMessage("");
    setReference(anchor.image_id);
    try {
      const cached = cachedReference.current;
      const initialFrame = cached?.id === anchor.image_id ? cached.image : await fetchExposure(
        api, timeline, anchor, controller.signal,
      );
      if (controller.signal.aborted) return;
      cachedReference.current = { id: anchor.image_id, image: initialFrame };
      setBusy(false);
      const seen = new Set<string>();
      let played = 0;
      let skipped = 0;
      for (const item of pool) {
        if (controller.signal.aborted) return;
        if (item.collection !== anchor.collection || !observationIdForExposure(item) ||
            seen.has(item.observed_at_utc)) continue;
        let image: RenderedExposure;
        try {
          [image] = await Promise.all([
            item === anchor ? Promise.resolve(initialFrame) : fetchExposure(
              api, timeline, item, controller.signal, initialFrame.scale,
            ),
            new Promise<void>((resolve) => window.setTimeout(resolve, played ? 900 : 0)),
          ]);
        } catch (error) {
          if (!isUnavailableExposure(error)) throw error;
          skipped++;
          continue;
        }
        if (controller.signal.aborted) return;
        if (item !== anchor && !(await shareCoverage(initialFrame, image))) {
          skipped++;
          continue;
        }
        if (controller.signal.aborted) return;
        seen.add(item.observed_at_utc);
        setCurrent({ selected: item, frame: image.frame });
        played++;
      }
      if (!controller.signal.aborted) {
        setMessage(played > 1
          ? `Reprodução concluída. ${played} exposições compatíveis exibidas${skipped ? ` e ${skipped} sem compatibilidade confirmada` : ""}.`
          : "Nenhuma outra exposição do detector teve cobertura suficiente em comum.");
      }
    } catch (error) {
      if (!controller.signal.aborted) setMessage(apiErrorMessage(error));
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setBusy(false);
        setPlaying(false);
      }
    }
  }

  function move(direction: number) {
    const next = exposures[index + direction];
    if (next && !busy && !playing) void choose(next, true);
  }

  function keyboard(event: KeyboardEvent<HTMLElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    move(event.key === "ArrowLeft" ? -1 : 1);
  }

  const swipe = useSkySwipe(move);

  return (
    <section className="viewer timeline-viewer" aria-label="Linha do tempo">
      <div className="timeline-title">
        <div><h2>Linha do tempo</h2><p className="muted">{days.size} dias UTC · {exposures.length} imagens no catálogo</p></div>
        <button className="button secondary" type="button" onClick={onClose}>Voltar à comparação</button>
      </div>
      {timeline.incomplete_collections.length > 0 && (
        <p role="status" className="error">O catálogo está parcial. Repita a busca em alguns minutos para consultar {timeline.incomplete_collections.join(", ")}.</p>
      )}
      {timeline.truncated && <p role="status" className="error">O IRSA atingiu o limite de exposições para esta consulta. O catálogo está parcial.</p>}
      {selected ? <>
        <div className="plate">
          <div className="plate-top instrument">
            <span>{formatDate(selected.observed_at_utc)} · {timeUTC.format(new Date(selected.observed_at_utc))} UTC</span>
            <span>{selected.collection} · {selected.detector}</span>
          </div>
          <div className="sky-wrap">
            <figure className="sky timeline-sky" ref={sky} tabIndex={0} onKeyDown={keyboard} {...swipe}
              aria-label="Recorte selecionado. Deslize na horizontal ou use as setas para navegar pelas exposições.">
              {frame ? <Image src={frame.image_src} width={128} height={128} loading="eager" draggable={false} alt="Recorte SPHEREx da exposição selecionada" />
                : <div className="timeline-placeholder">{busy ? "Carregando recorte…" : "Selecione uma exposição e abra o recorte."}</div>}
              {frame && <><span className="north instrument" aria-hidden="true">N ↑<br />E ←</span><span className="scale instrument" aria-hidden="true">1′</span></>}
            </figure>
          </div>
          <div className="plate-bottom instrument">
            <span>RA {timeline.ra_deg}° · DEC {timeline.dec_deg}°</span><span>6′ × 6′</span>
          </div>
        </div>
        <div className="timeline-inputs">
          <label>Dia de observação
            <select className="control-field" value={day} disabled={busy || playing} onChange={(event) => {
              const item = days.get(event.target.value)?.[0];
              if (item) void choose(item, true);
            }}>
              {dayOptions}
            </select>
          </label>
          <label>Horário UTC e detector
            <select className="control-field" value={selected.image_id} disabled={busy || playing} onChange={(event) => {
              const index = indexById.get(event.target.value);
              if (index !== undefined) void choose(exposures[index], true);
            }}>
              {days.get(day)?.map((item) => <option key={item.image_id} value={item.image_id}>
                {timeUTC.format(new Date(item.observed_at_utc))} · {item.detector} · {item.collection.replace("spherex_", "").toUpperCase()}
              </option>)}
            </select>
          </label>
        </div>
        <div className="timeline-actions">
          <button className="button secondary" type="button" aria-disabled={busy || playing || index <= 0} onClick={() => move(-1)}>Anterior</button>
          <button className="button secondary" type="button" aria-disabled={busy || playing || index >= exposures.length - 1} onClick={() => move(1)}>Próxima</button>
          {!frame && api && observationId && <button className="button primary" type="button" aria-disabled={busy}
            onClick={(event) => { if (!busy) void choose(selected, false, event.currentTarget); }}>Abrir recorte</button>}
          {api && <button className="button secondary" type="button" disabled={!playing && (!playable || busy)}
            onClick={() => playing ? pause() : void play()}>{playing ? "Pausar" : "Reproduzir faixa"}</button>}
          {!frame && cutout && <a className="button secondary" href={cutout} target="_blank" rel="noreferrer">Abrir FITS no IRSA</a>}
        </div>
        {api && <p className="viewer-hint">{reference
          ? "Escala de brilho fixada pela referência nas imagens do mesmo detector com cobertura em comum."
          : "A reprodução usa a escala de brilho da exposição selecionada nos recortes do mesmo detector."}</p>}
        {!api && <p className="viewer-hint">Catálogo salvo. Os quadros do exemplo ficam disponíveis aqui. Para as demais exposições, abra o link do FITS.</p>}
        <p role="status" className="viewer-hint timeline-status">{busy ? "Carregando recorte…" : message}</p>
        <p aria-live={playing ? "off" : "polite"} aria-atomic="true" className="sr-only">
          Exposição selecionada em {formatDate(selected.observed_at_utc)}, {timeUTC.format(new Date(selected.observed_at_utc))} UTC, detector {selected.detector}.
        </p>
        <details className="sources">
          <summary>Origem e processamento</summary>
          <dl>
            <dt>Observação UTC</dt><dd>{frame?.observed_at_utc ?? selected.observed_at_utc}</dd>
            {observationId && <><dt>ID da observação</dt><dd>{observationId}</dd></>}
            {selected.observation && !frame && <><dt>Faixa do detector</dt><dd>{selected.observation.minWavelength}–{selected.observation.maxWavelength} µm</dd></>}
            {frame && <>
              <dt>{isLiveFrame ? "Faixa do detector" : "Faixa no centro"}</dt><dd>{frame.wavelength_um.toFixed(5)} µm · largura {frame.bandwidth_um.toFixed(5)} µm</dd>
              <dt>Cobertura válida</dt><dd>{(frame.valid_fraction * 100).toFixed(1)}%</dd></>}
            {source && <><dt>FITS original</dt><dd><a href={source} target="_blank" rel="noreferrer">Exposição no IRSA ↗</a></dd></>}
            {cutout && <><dt>Recorte</dt><dd><a href={cutout} target="_blank" rel="noreferrer">Arquivo FITS ↗</a></dd></>}
          </dl>
        </details>
      </> : <p className="viewer-hint">Nenhuma exposição encontrada para este campo.</p>}
    </section>
  );
}
