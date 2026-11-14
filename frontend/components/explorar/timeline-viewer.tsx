"use client";

import Image from "next/image";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { formatDate, isFrame, isRecord, sourceLink, type Frame } from "../../lib/sequence";
import type { CatalogExposure, Timeline } from "../../lib/timeline";
import { apiErrorDetail } from "../../lib/api-error";
import { useSkySwipe } from "./use-sky-swipe";

const timeUTC = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC",
});

export default function TimelineViewer({ timeline, api, savedFrames, onClose }: {
  timeline: Timeline; api?: string; savedFrames: Frame[]; onClose: () => void;
}) {
  const exposures = timeline.exposures;
  const days = new Map<string, typeof exposures>();
  for (const exposure of exposures) {
    const day = exposure.observed_at_utc.slice(0, 10);
    const group = days.get(day);
    if (group) group.push(exposure);
    else days.set(day, [exposure]);
  }
  const initial = exposures.find((item) => item.frame_id === savedFrames[0]?.frame_id);
  const [selected, setSelected] = useState(initial ?? exposures[0]);
  const [frame, setFrame] = useState<Frame | undefined>(initial ? savedFrames[0] : undefined);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [message, setMessage] = useState("");
  const [reference, setReference] = useState<string>();
  const pending = useRef<AbortController | null>(null);
  const day = selected?.observed_at_utc.slice(0, 10) ?? "";
  const index = selected ? exposures.indexOf(selected) : -1;
  const playable = selected && api && frame && exposures.some(
    (item) => item.image_id !== selected.image_id && item.detector === selected.detector &&
      item.observed_at_utc !== selected.observed_at_utc,
  );

  useEffect(() => () => pending.current?.abort(), []);

  async function load(id: string, signal: AbortSignal, anchor?: string): Promise<Frame | null> {
    const item = exposures.find((exposure) => exposure.image_id === id);
    const local = savedFrames.find((image) => image.frame_id === item?.frame_id);
    if (!api) {
      if (local) return local;
      throw new Error("Abra o FITS no IRSA. A prévia deste recorte precisa da API.");
    }
    const params = new URLSearchParams({
      ra_deg: String(timeline.ra_deg), dec_deg: String(timeline.dec_deg), image_id: id,
    });
    if (anchor) params.set("reference_id", anchor);
    const response = await fetch(`${api}/api/v1/timeline/frame?${params}`, {
      signal: AbortSignal.any([signal, AbortSignal.timeout(90_000)]),
    });
    const data: unknown = await response.json().catch(() => null);
    const detail = apiErrorDetail(data);
    const error = isRecord(detail) ? detail : undefined;
    if (anchor && anchor !== id && (
      response.status === 409 || response.status === 404 ||
      error?.code === "archive_unavailable" || response.status === 504
    )) return null;
    if (!response.ok) throw new Error(typeof error?.message === "string" ? error.message : "Não foi possível carregar o recorte. Tente novamente.");
    if (!isFrame(data) || !data.image_src.startsWith("data:image/png;base64,")) {
      throw new Error("A API devolveu uma imagem inválida.");
    }
    return data;
  }

  function pause() {
    pending.current?.abort();
    pending.current = null;
    setPlaying(false);
    setBusy(false);
  }

  async function choose(item: CatalogExposure, reuseSaved = false) {
    pause();
    setSelected(item);
    setReference(undefined);
    setMessage("");
    const local = reuseSaved && savedFrames.find((image) => image.frame_id === item.frame_id);
    setFrame(local || undefined);
    if (local) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try {
      const image = await load(item.image_id, controller.signal);
      if (!controller.signal.aborted && image) setFrame(image);
    } catch (error) {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "Não foi possível carregar.");
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setBusy(false);
      }
    }
  }

  async function play() {
    if (!selected || !playable || busy || pending.current) return;
    const anchor = exposures.find((item) => item.image_id === reference) ?? selected;
    const pool = exposures.filter((item) => item.detector === anchor.detector);
    const controller = new AbortController();
    pending.current = controller;
    setPlaying(true);
    setBusy(true);
    setMessage("");
    setReference(anchor.image_id);
    try {
      const initialFrame = await load(anchor.image_id, controller.signal, anchor.image_id);
      if (controller.signal.aborted) return;
      if (!initialFrame) throw new Error("A referência está indisponível.");
      setBusy(false);
      const seen = new Set<string>();
      let played = 0;
      let skipped = 0;
      for (const item of pool) {
        if (controller.signal.aborted) return;
        if (seen.has(item.observed_at_utc)) continue;
        const [image] = await Promise.all([
          item === anchor ? Promise.resolve(initialFrame) :
          load(item.image_id, controller.signal, anchor.image_id),
          new Promise<void>((resolve) => window.setTimeout(resolve, played ? 900 : 0)),
        ]);
        if (controller.signal.aborted) return;
        if (!image) {
          skipped++;
          continue;
        }
        seen.add(item.observed_at_utc);
        setFrame(image);
        setSelected(item);
        played++;
      }
      if (!controller.signal.aborted) {
        setMessage(played > 1
          ? `Reprodução concluída. ${played} exposições compatíveis exibidas${skipped ? ` e ${skipped} sem compatibilidade confirmada` : ""}.`
          : "Nenhuma outra exposição passou nas verificações de faixa e cobertura.");
      }
    } catch {
      if (!controller.signal.aborted) setMessage("A reprodução foi interrompida. Pressione Reproduzir faixa para tentar novamente.");
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
      {selected ? <>
        <div className="plate">
          <div className="plate-top instrument">
            <span>{formatDate(selected.observed_at_utc)} · {timeUTC.format(new Date(selected.observed_at_utc))} UTC</span>
            <span>{selected.collection} · {selected.detector}</span>
          </div>
          <div className="sky-wrap">
            <figure className="sky timeline-sky" tabIndex={0} onKeyDown={keyboard} {...swipe}
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
              {[...days].map(([date, items]) => <option key={date} value={date}>{formatDate(items[0].observed_at_utc)} · {items.length} imagens</option>)}
            </select>
          </label>
          <label>Horário UTC e detector
            <select className="control-field" value={selected.image_id} disabled={busy || playing} onChange={(event) => {
              const item = exposures.find((exposure) => exposure.image_id === event.target.value);
              if (item) void choose(item, true);
            }}>
              {days.get(day)?.map((item) => <option key={item.image_id} value={item.image_id}>
                {timeUTC.format(new Date(item.observed_at_utc))} · {item.detector} · {item.collection.replace("spherex_", "").toUpperCase()}
              </option>)}
            </select>
          </label>
        </div>
        <div className="timeline-actions">
          <button className="button secondary" type="button" disabled={busy || playing || index <= 0} onClick={() => move(-1)}>Anterior</button>
          <button className="button secondary" type="button" disabled={busy || playing || index >= exposures.length - 1} onClick={() => move(1)}>Próxima</button>
          {!frame && api && <button className="button primary" type="button" disabled={busy} onClick={() => void choose(selected)}>Abrir recorte</button>}
          {api && <button className="button secondary" type="button" disabled={!playing && (!playable || busy)}
            onClick={() => playing ? pause() : void play()}>{playing ? "Pausar" : "Reproduzir faixa"}</button>}
          {!api && !frame && <a className="button secondary" href={sourceLink(selected.cutout_url)} target="_blank" rel="noreferrer">Abrir FITS no IRSA</a>}
        </div>
        {api && <p className="viewer-hint">{reference
          ? "Contraste fixado pela exposição de referência. A reprodução testa faixa espectral e cobertura."
          : "A reprodução usa a exposição selecionada como referência e avança pelas imagens compatíveis."}</p>}
        {!api && <p className="viewer-hint">Catálogo salvo. Os quadros do exemplo ficam disponíveis aqui. Para as demais exposições, abra o link do FITS.</p>}
        {message && <p role="status" className="viewer-hint">{message}</p>}
        <details className="sources">
          <summary>Origem e processamento</summary>
          <dl>
            <dt>Observação UTC</dt><dd>{frame?.observed_at_utc ?? selected.observed_at_utc}</dd>
            {frame && <><dt>Faixa no centro</dt><dd>{frame.wavelength_um.toFixed(5)} µm · largura {frame.bandwidth_um.toFixed(5)} µm</dd>
              <dt>Cobertura válida</dt><dd>{(frame.valid_fraction * 100).toFixed(1)}%</dd></>}
            <dt>FITS original</dt><dd><a href={sourceLink(selected.source_url)} target="_blank" rel="noreferrer">Exposição no IRSA ↗</a></dd>
            <dt>Recorte</dt><dd><a href={sourceLink(selected.cutout_url)} target="_blank" rel="noreferrer">Arquivo FITS ↗</a></dd>
          </dl>
        </details>
      </> : <p className="viewer-hint">Nenhuma exposição encontrada para este campo.</p>}
    </section>
  );
}
