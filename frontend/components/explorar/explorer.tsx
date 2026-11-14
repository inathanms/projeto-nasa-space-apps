"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { formatDate, isRecord, isSequence, sourceLink, type Example, type Sequence } from "../../lib/sequence";
import { isTimeline, type Timeline } from "../../lib/timeline";
import { exampleAliases } from "../../content/examples";
import { apiErrorDetail } from "../../lib/api-error";
import { parseCoordinate } from "../../lib/coordinates";
import { useSkySwipe } from "./use-sky-swipe";

const SpherexOrbit = dynamic(() => import("./spherex-orbit"), {
  ssr: false,
  loading: () => <p className="orbit muted" role="status">Carregando a visualização da órbita…</p>,
});
const TimelineViewer = dynamic(() => import("./timeline-viewer"), {
  ssr: false,
  loading: () => <p className="muted" role="status">Carregando a linha do tempo…</p>,
});

const API = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "");
const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 5 });
const dateTime = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "medium", timeStyle: "medium", timeZone: "UTC",
});
const timestamp = (date: string | null) =>
  date && Number.isFinite(Date.parse(date)) ? dateTime.format(new Date(date)) + " UTC" : "—";

export default function Explorer({ examples }: { examples: [Example, ...Example[]] }) {
  const [example, setExample] = useState<Example | null>(examples[0]);
  const [sequence, setSequence] = useState<Sequence>(examples[0].sequence);
  const [selected, setSelected] = useState(examples[0].slug);
  const [ra, setRa] = useState(String(examples[0].sequence.ra_deg));
  const [dec, setDec] = useState(String(examples[0].sequence.dec_deg));
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [timelineVersion, setTimelineVersion] = useState(0);
  const [invalid, setInvalid] = useState<"ra" | "dec" | "">("");
  const active = useRef<AbortController | null>(null);
  const raInput = useRef<HTMLInputElement>(null);
  const decInput = useRef<HTMLInputElement>(null);
  const frame = sequence.frames[index];
  const hasGuide = example?.slug === "eps-indi-b";

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedSlug = params.get("exemplo") ?? params.get("alvo") ?? "";
    const slug = exampleAliases[requestedSlug] ?? requestedSlug;
    const preset = examples.find((item) => item.slug === slug);
    if (preset) {
      setSelected(preset.slug);
      setExample(preset);
      setSequence(preset.sequence);
      setRa(String(preset.sequence.ra_deg));
      setDec(String(preset.sequence.dec_deg));
    }
    if (params.get("modo") === "epocas") void openSavedTimeline();
    if (params.has("ra_deg") && params.has("dec_deg") && params.get("modo") !== "epocas") {
      const requestedRA = parseCoordinate(params.get("ra_deg") ?? "");
      const requestedDec = parseCoordinate(params.get("dec_deg") ?? "");
      if (requestedRA >= 0 && requestedRA < 360 && requestedDec >= -90 && requestedDec <= 90) {
        setRa(String(requestedRA));
        setDec(String(requestedDec));
      }
    }
    return () => {
      active.current?.abort();
      active.current = null;
    };
  }, [examples]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setIndex((previous) => 1 - previous), 900);
    return () => window.clearInterval(timer);
  }, [playing]);

  function showExample() {
    const preset = examples.find((item) => item.slug === selected) ?? examples[0];
    active.current?.abort();
    active.current = null;
    setBusy(false);
    setPlaying(false);
    setShowGuide(false);
    setIndex(0);
    setError("");
    setInvalid("");
    setExample(preset);
    setSequence(preset.sequence);
    setTimeline(null);
    setRa(String(preset.sequence.ra_deg));
    setDec(String(preset.sequence.dec_deg));
  }

  async function search(event: FormEvent<HTMLFormElement>, catalog = false) {
    event.preventDefault();
    if (active.current) return;
    const r = parseCoordinate(ra);
    const d = parseCoordinate(dec);
    if (!Number.isFinite(r) || r < 0 || r >= 360) {
      setInvalid("ra");
      setError("Informe uma ascensão reta entre 0° (inclusive) e 360° (exclusive).");
      raInput.current?.focus();
      return;
    }
    if (!Number.isFinite(d) || d < -90 || d > 90) {
      setInvalid("dec");
      setError("Informe uma declinação entre −90° e +90°.");
      decInput.current?.focus();
      return;
    }
    if (!API && catalog && r === 331.0954 && d === -56.8008) {
      await openSavedTimeline();
      return;
    }
    if (!API) {
      setError("A consulta ao IRSA não está configurada neste ambiente. Você pode comparar os quadros do exemplo abaixo.");
      return;
    }
    const request = new AbortController();
    active.current = request;
    const timeout = window.setTimeout(() => request.abort(), 110_000);
    setError("");
    setInvalid("");
    setBusy(true);
    setPlaying(false);
    try {
      const query = new URLSearchParams({ ra_deg: String(r), dec_deg: String(d) });
      const endpoint = catalog ? "timeline" : "sequence";
      const response = await fetch(`${API}/api/v1/${endpoint}?${query}`, { signal: request.signal });
      const payload: unknown = await response.json().catch(() => null);
      const detail = apiErrorDetail(payload);
      const code = isRecord(detail) ? detail.code : undefined;
      if (active.current !== request) return;
      if (response.status === 404 && code === "insufficient_coverage") {
        setError("O arquivo não retornou dois quadros comparáveis para esse campo. Tente outras coordenadas ou abra o exemplo.");
      } else if (response.status === 422) {
        const first: unknown = Array.isArray(detail) ? detail[0] : null;
        const location = isRecord(first) && Array.isArray(first.loc) ? first.loc : [];
        const field = location.includes("ra_deg") ? "ra" : location.includes("dec_deg") ? "dec" : "";
        setInvalid(field);
        setError(field === "ra" ? "Confira o valor da ascensão reta." : field === "dec" ? "Confira o valor da declinação." : "Confira os valores de RA e Dec.");
        if (field === "ra") raInput.current?.focus();
        if (field === "dec") decInput.current?.focus();
      } else if (response.status === 503 && code === "server_busy") {
        setError("Outra busca está em andamento. Tente novamente em instantes ou abra o exemplo.");
      } else if (response.status === 504) {
        setError("A consulta ao arquivo demorou mais do que o esperado. Você pode abrir o exemplo enquanto isso.");
      } else if (!response.ok) {
        setError("O serviço está temporariamente indisponível. Você pode abrir o exemplo.");
      } else if (catalog && isTimeline(payload)) {
        setTimeline(payload);
        setTimelineVersion((version) => version + 1);
      } else if (!catalog && isSequence(payload)) {
        setTimeline(null);
        setSequence(payload);
        setExample(null);
        setShowGuide(false);
        setPlaying(false);
        setIndex(0);
      } else {
        setError("O serviço devolveu dados em um formato inesperado.");
      }
    } catch {
      if (active.current === request) {
        setError(request.signal.aborted
          ? "A consulta demorou mais do que o esperado. Você pode abrir o exemplo."
          : "Não foi possível conectar ao serviço. Você pode abrir o exemplo.");
      }
    } finally {
      window.clearTimeout(timeout);
      if (active.current === request) {
        active.current = null;
        setBusy(false);
      }
    }
  }

  async function openSavedTimeline() {
    if (active.current) return;
    const request = new AbortController();
    active.current = request;
    setBusy(true);
    setPlaying(false);
    setError("");
    try {
      const response = await fetch("/examples/eps-indi-b/timeline.json", { signal: request.signal });
      const payload: unknown = await response.json();
      if (!response.ok || !isTimeline(payload)) throw new Error();
      if (!request.signal.aborted) {
        setRa(String(payload.ra_deg));
        setDec(String(payload.dec_deg));
        setTimeline(payload);
        setTimelineVersion((version) => version + 1);
      }
    } catch {
      if (!request.signal.aborted) setError("Não foi possível abrir o catálogo salvo.");
    } finally {
      if (active.current === request) {
        active.current = null;
        setBusy(false);
      }
    }
  }

  function chooseFrame(next: number) {
    setPlaying(false);
    setIndex(next);
  }

  function keyboard(event: KeyboardEvent<HTMLElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    chooseFrame(1 - index);
  }

  const swipe = useSkySwipe(() => chooseFrame(1 - index));
  const observedLabel = example?.synthetic ? "Data ilustrativa" : "Observação";
  const source = sourceLink(frame.source_url);
  const cutout = sourceLink(frame.cutout_url);

  return (
    <>
      <div className="explorer-grid">
        <aside className="controls" aria-label="Escolha do campo">
          <form onSubmit={(event) => void search(event, (event.nativeEvent as SubmitEvent).submitter?.id !== "compare-pair")} noValidate>
            <h2>Buscar por coordenadas</h2>
            <p className="muted">Use graus decimais no sistema ICRS.</p>
            <label htmlFor="ra">Ascensão reta <span>RA</span></label>
            <input className="control-field" ref={raInput} id="ra" name="ra_deg" inputMode="decimal" value={ra} readOnly={busy} onChange={(event) => {
              setRa(event.target.value);
              if (invalid === "ra") {
                setInvalid("");
                setError("");
              }
            }} aria-invalid={invalid === "ra"} aria-describedby={invalid === "ra" ? "search-error" : undefined} />
            <label htmlFor="dec">Declinação <span>DEC</span></label>
            <input className="control-field" ref={decInput} id="dec" name="dec_deg" inputMode="decimal" value={dec} readOnly={busy} onChange={(event) => {
              setDec(event.target.value);
              if (invalid === "dec") {
                setInvalid("");
                setError("");
              }
            }} aria-invalid={invalid === "dec"} aria-describedby={invalid === "dec" ? "search-error" : undefined} />
            <button className="button primary" type="submit" disabled={busy}>{busy ? "Consultando…" : "Buscar épocas no IRSA"}<span aria-hidden="true">↗</span></button>
            {API && <button id="compare-pair" className="button secondary" type="submit" disabled={busy}>Buscar par para comparação</button>}
            <p className="muted offline-note"><Link href="/laboratorio/">Ajustar coordenadas no globo 3D</Link></p>
            {!API && <p className="muted offline-note">A busca ao vivo requer uma API configurada neste ambiente.</p>}
            {busy && <p role="status" className="muted offline-note">Carregando observações…</p>}
            {error && <p id="search-error" className="error" role="alert">{error}</p>}
          </form>
          <div className="preset">
            <h2>Exemplo offline</h2>
            <label htmlFor="preset">Campo de observação</label>
            <select className="control-field" id="preset" value={selected} onChange={(event) => setSelected(event.target.value)}>
              {examples.map((item) => <option key={item.slug} value={item.slug}>{item.name}{item.synthetic ? " · simulação" : ""}</option>)}
            </select>
            <button type="button" className="button secondary" onClick={showExample}>Abrir exemplo <span aria-hidden="true">↗</span></button>
            <button type="button" className="button secondary" disabled={busy} onClick={() => void openSavedTimeline()}>Épocas de Epsilon Indi B</button>
          </div>
        </aside>

        {timeline ? <TimelineViewer key={timelineVersion}
          timeline={timeline} api={API}
          savedFrames={examples.find((item) => item.sequence.ra_deg === timeline.ra_deg && item.sequence.dec_deg === timeline.dec_deg)?.sequence.frames ?? []}
          onClose={() => setTimeline(null)} />
        : <section aria-label="Visor de comparação" className="viewer">
          <div className="plate">
            <div className="plate-top instrument">
              <span>{example?.name ?? "Campo consultado"}</span>
              <span>{example?.synthetic ? "SIMULAÇÃO" : example ? "EXEMPLO REAL" : "IRSA · AO VIVO"}</span>
            </div>
            <div className="sky-wrap">
              <figure id="sky-field" className="sky" tabIndex={0} onKeyDown={keyboard} {...swipe} aria-label="Campo de comparação. Deslize na horizontal ou use as setas para alternar as épocas.">
                {sequence.frames.map((image, i) => (
                  <Image key={image.frame_id} src={image.image_src} width={360} height={360} loading="eager" draggable={false}
                    alt={`Época ${i + 1}: ${formatDate(image.observed_at_utc)}`}
                    className={index === i ? "" : "hidden-frame"} aria-hidden={index !== i} />
                ))}
                <span className="north instrument" aria-hidden="true">N ↑<br />E ←</span>
                <span className="scale instrument" aria-hidden="true">1′</span>
                {hasGuide && showGuide && <span className="sky-guide" aria-hidden="true" />}
              </figure>
            </div>
            <div className="plate-bottom instrument">
              <span>RA {number.format(sequence.ra_deg)}° · DEC {number.format(sequence.dec_deg)}°</span>
              <span>{sequence.fov_arcmin}′ × {sequence.fov_arcmin}′</span>
            </div>
          </div>

          <div className="transport">
            <label className="epoch-range">
              <span>Época exibida</span>
              <input type="range" min={0} max={1} step={1} value={index}
                aria-valuetext={formatDate(frame.observed_at_utc)}
                onChange={(event) => chooseFrame(event.currentTarget.valueAsNumber)} />
            </label>
            <div className="epochs" role="group" aria-label="Época exibida">
              {sequence.frames.map((item, i) => (
                <button className="epoch" type="button" key={item.frame_id} aria-pressed={index === i} onClick={() => chooseFrame(i)}>
                  <span className="instrument">ÉPOCA 0{i + 1}</span><span>{formatDate(item.observed_at_utc)}</span>
                </button>
              ))}
            </div>
            <button className="button secondary playback" type="button" onClick={() => setPlaying((previous) => !previous)}>
              <span aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span> {playing ? "Pausar" : "Reproduzir"}
            </button>
          </div>
          <div aria-live={playing ? "off" : "polite"} className="sr-only">{observedLabel}: {timestamp(frame.observed_at_utc)}</div>
          {hasGuide ? (
            <div className="viewer-guide">
              <p>Procure Epsilon Indi B perto do centro. Ao alternar as épocas, a fonte se desloca ligeiramente para a esquerda e para baixo em relação às estrelas do campo.</p>
              <button className="button secondary" type="button" aria-pressed={showGuide} aria-controls="sky-field" onClick={() => setShowGuide((visible) => !visible)}>
                Marcar região da fonte
              </button>
            </div>
          ) : (
            <p className="viewer-hint">{example?.synthetic ? "Imagens simuladas. Procure o ponto que muda de posição." : "Confira qualquer mudança aparente nos dados de origem."}</p>
          )}
          <p className="viewer-hint">Deslize na horizontal ou use ← → no visor para alternar.</p>
          <details className="sources">
            <summary>Origem e processamento</summary>
            <dl>
              <dt>{observedLabel}</dt><dd>{timestamp(frame.observed_at_utc)}</dd>
              <dt>Coleção e detector</dt><dd>{frame.collection} · {frame.detector}</dd>
              <dt>Faixa no centro</dt><dd>{number.format(frame.wavelength_um)} µm · largura {number.format(frame.bandwidth_um)} µm</dd>
              <dt>Cobertura válida</dt><dd>{number.format(frame.valid_fraction * 100)}%</dd>
              <dt>Calibração</dt><dd>{frame.calibration_version}</dd>
              <dt>Recuperado em</dt><dd>{timestamp(sequence.fetched_at_utc)}</dd>
              <dt>Processamento</dt><dd>{sequence.processing_version} · {timestamp(sequence.generated_at_utc)}</dd>
              <dt>Produto</dt><dd>{source ? <a href={source} target="_blank" rel="noreferrer">Exposição no IRSA ↗</a> : "Sem produto de origem"}</dd>
              {cutout && <><dt>Recorte</dt><dd><a href={cutout} target="_blank" rel="noreferrer">Arquivo FITS ↗</a></dd></>}
            </dl>
          </details>
        </section>}
      </div>
      <SpherexOrbit observedAt={timeline || example?.synthetic ? null : frame.observed_at_utc} />
    </>
  );
}
