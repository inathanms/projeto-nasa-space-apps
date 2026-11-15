"use client";

import { useLocale } from "../ui/LocaleProvider";
import { forLocales } from "../../lib/i18n";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useEffectEvent, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { formatDate, sourceLink, type Example, type Sequence } from "../../lib/sequence";
import { isTimeline, type Timeline } from "../../lib/timeline";
import { exampleAliases, exampleDescriptions } from "../../content/examples";
import { apiErrorMessage, fetchComparison, fetchEpochs } from "../../lib/spherex-api";
import { parseCoordinate } from "../../lib/coordinates";
import ComparisonReadout from "./comparison-readout";
import { useSkySwipe } from "./use-sky-swipe";

const SpherexOrbit = dynamic(() => import("./spherex-orbit"), {
  ssr: false,
  loading: OrbitLoading,
});
const TimelineViewer = dynamic(() => import("./timeline-viewer"), {
  ssr: false,
  loading: TimelineLoading,
});

function OrbitLoading() {
  const { t } = useLocale();
  return <p className="orbit muted" role="status">{t("Carregando a visualização da órbita…")}</p>;
}

function TimelineLoading() {
  const { t } = useLocale();
  return <p className="muted" role="status">{t("Carregando a linha do tempo…")}</p>;
}

const API = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "");
const numbers = forLocales((language) => new Intl.NumberFormat(language, { maximumFractionDigits: 5 }));
const dateTimes = forLocales((language) => new Intl.DateTimeFormat(language, {
  dateStyle: "medium", timeStyle: "medium", timeZone: "UTC",
}));

export default function Explorer({ examples }: { examples: [Example, ...Example[]] }) {
  const { t, locale, href } = useLocale();
  const number = numbers[locale];
  const dateTime = dateTimes[locale];
  const timestamp = (date: string | null) =>
    date && Number.isFinite(Date.parse(date)) ? dateTime.format(new Date(date)) + " UTC" : "—";
  const [example, setExample] = useState<Example | null>(examples[0]);
  const [sequence, setSequence] = useState<Sequence | null>(examples[0].sequence);
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
  const results = useRef<HTMLDivElement>(null);
  const revealFrom = useRef<HTMLElement | null>(null);
  const timelineTrigger = useRef<HTMLElement | null>(null);
  const raInput = useRef<HTMLInputElement>(null);
  const decInput = useRef<HTMLInputElement>(null);
  const frame = sequence?.frames[index];
  const hasGuide = example?.slug === "eps-indi-b";

  const openLinkedField = useEffectEvent(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedSlug = params.get("exemplo") ?? params.get("alvo") ?? "";
    const slug = exampleAliases[requestedSlug] ?? requestedSlug;
    const requestedRA = parseCoordinate(params.get("ra_deg") ?? "");
    const requestedDec = parseCoordinate(params.get("dec_deg") ?? "");
    const hasField = requestedRA >= 0 && requestedRA < 360 && requestedDec >= -90 && requestedDec <= 90;
    const mode = params.get("modo");
    if (mode === "epocas" && (!hasField || (requestedRA === 331.0954 && requestedDec === -56.8008))) {
      void openSavedTimeline();
      return;
    }
    const preset = examples.find((item) => item.slug === slug) ??
      (hasField && !mode ? examples.find(({ sequence }) =>
        Number(sequence.ra_deg.toFixed(6)) % 360 === requestedRA &&
        Number(sequence.dec_deg.toFixed(6)) === requestedDec,
      ) : undefined);
    if (preset) {
      applyExample(preset);
      return;
    }
    if (!hasField) return;
    setRa(String(requestedRA));
    setDec(String(requestedDec));
    setExample(null);
    setSequence(null);
    if (mode === "consultar" || mode === "epocas") void requestField(requestedRA, requestedDec, true);
  });

  useEffect(() => {
    openLinkedField();
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

  useEffect(() => {
    if (revealFrom.current && document.activeElement === revealFrom.current) results.current?.focus();
    revealFrom.current = null;
  }, [sequence, timeline]);

  function applyExample(preset: Example, trigger?: HTMLElement) {
    active.current?.abort();
    active.current = null;
    revealFrom.current = trigger ?? null;
    setBusy(false);
    setPlaying(false);
    setShowGuide(false);
    setIndex(0);
    setError("");
    setInvalid("");
    setSelected(preset.slug);
    setExample(preset);
    setSequence(preset.sequence);
    setTimeline(null);
    setRa(String(preset.sequence.ra_deg));
    setDec(String(preset.sequence.dec_deg));
  }

  function search(event: FormEvent<HTMLFormElement>, catalog = false) {
    event.preventDefault();
    if (active.current) return;
    const r = parseCoordinate(ra);
    const d = parseCoordinate(dec);
    if (!Number.isFinite(r) || r < 0 || r >= 360) {
      setInvalid("ra");
      setError(t("Informe uma ascensão reta entre 0° (inclusive) e 360° (exclusive)."));
      raInput.current?.focus();
      return;
    }
    if (!Number.isFinite(d) || d < -90 || d > 90) {
      setInvalid("dec");
      setError(t("Informe uma declinação entre −90° e +90°."));
      decInput.current?.focus();
      return;
    }
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : undefined;
    void requestField(r, d, catalog, trigger);
  }

  async function requestField(r: number, d: number, catalog: boolean, trigger?: HTMLElement) {
    if (!API && catalog && r === 331.0954 && d === -56.8008) {
      await openSavedTimeline(trigger);
      return;
    }
    if (!API) {
      setError(t("A consulta ao IRSA não está configurada neste ambiente. Você pode comparar os quadros do exemplo abaixo."));
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
      const epochs = await fetchEpochs(API, r, d, request.signal);
      if (active.current !== request) return;
      if (catalog) {
        revealFrom.current = trigger ?? null;
        timelineTrigger.current = trigger ?? null;
        setTimeline(epochs);
        setTimelineVersion((version) => version + 1);
      } else {
        const pair = await fetchComparison(API, epochs, request.signal, locale);
        request.signal.throwIfAborted();
        if (active.current !== request) return;
        revealFrom.current = trigger ?? null;
        setTimeline(null);
        setSequence(pair);
        setExample(null);
        setShowGuide(false);
        setPlaying(false);
        setIndex(0);
      }
    } catch (cause) {
      if (active.current === request) {
        setError(apiErrorMessage(cause, locale));
      }
    } finally {
      window.clearTimeout(timeout);
      if (active.current === request) {
        active.current = null;
        setBusy(false);
      }
    }
  }

  async function openSavedTimeline(trigger?: HTMLElement) {
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
        revealFrom.current = trigger ?? null;
        timelineTrigger.current = trigger ?? null;
        setRa(String(payload.ra_deg));
        setDec(String(payload.dec_deg));
        setTimeline(payload);
        setTimelineVersion((version) => version + 1);
      }
    } catch {
      if (!request.signal.aborted) setError(t("Não foi possível abrir o catálogo salvo."));
    } finally {
      if (active.current === request) {
        active.current = null;
        setBusy(false);
      }
    }
  }

  function closeTimeline() {
    const trigger = timelineTrigger.current;
    timelineTrigger.current = null;
    setTimeline(null);
    (trigger?.isConnected ? trigger : results.current)?.focus();
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
  const observedLabel = example?.synthetic ? t("Data ilustrativa") : t("Observação");
  const source = sourceLink(frame?.source_url ?? null);
  const cutout = sourceLink(frame?.cutout_url ?? null);
  const exampleDescription = example && exampleDescriptions(locale)[example.slug];

  return (
    <>
      <div className="explorer-grid">
        <aside className="controls" aria-label={t("Escolha do campo")}>
          <form onSubmit={(event) => void search(event, (event.nativeEvent as SubmitEvent).submitter?.id !== "compare-pair")} noValidate>
            <h2>{t("Buscar por coordenadas")}</h2>
            <p className="muted" id="coordinate-format">{t("Use graus decimais no sistema ICRS.")}</p>
            <label htmlFor="ra">{t("Ascensão reta")} <span>RA</span></label>
            <input className="control-field" ref={raInput} id="ra" name="ra_deg" inputMode="decimal" value={ra} readOnly={busy} onChange={(event) => {
              setRa(event.target.value);
              if (invalid === "ra") {
                setInvalid("");
                setError("");
              }
            }} aria-invalid={invalid === "ra"} aria-describedby={invalid === "ra" ? "coordinate-format search-error" : "coordinate-format"} />
            <label htmlFor="dec">{t("Declinação")} <span>DEC</span></label>
            <input className="control-field" ref={decInput} id="dec" name="dec_deg" inputMode="decimal" value={dec} readOnly={busy} onChange={(event) => {
              setDec(event.target.value);
              if (invalid === "dec") {
                setInvalid("");
                setError("");
              }
            }} aria-invalid={invalid === "dec"} aria-describedby={invalid === "dec" ? "coordinate-format search-error" : "coordinate-format"} />
            <button className="button primary" type="submit" aria-disabled={busy} aria-controls="resultado-explorador">{t("Buscar épocas no IRSA")}<span aria-hidden="true">↗</span></button>
            {API && <button id="compare-pair" className="button secondary" type="submit" aria-disabled={busy}
              aria-controls="resultado-explorador">{t("Buscar par para comparação")}</button>}
            <p className="muted offline-note"><Link href={href("/laboratorio/")}>{t("Ajustar coordenadas no globo 3D")}</Link></p>
            {!API && <p className="muted offline-note">{t("A busca ao vivo requer uma API configurada neste ambiente.")}</p>}
            <p role="status" className="muted search-feedback">{busy ? t("Carregando observações…") : ""}</p>
            <p id="search-error" className="error search-feedback" role="alert">{error}</p>
          </form>
          <div className="preset">
            <h2>{t("Exemplo offline")}</h2>
            <label htmlFor="preset">{t("Campo de observação")}</label>
            <select className="control-field" id="preset" value={selected} onChange={(event) => setSelected(event.target.value)}>
              {examples.map((item) => <option key={item.slug} value={item.slug}>{item.name}{item.synthetic ? t(" · simulação") : ""}</option>)}
            </select>
            <button type="button" className="button secondary" aria-controls="resultado-explorador"
              onClick={(event) => applyExample(examples.find((item) => item.slug === selected) ?? examples[0], event.currentTarget)}>{t("Abrir exemplo")} <span aria-hidden="true">↗</span></button>
            <button type="button" className="button secondary" aria-disabled={busy} aria-controls="resultado-explorador"
              onClick={(event) => void openSavedTimeline(event.currentTarget)}>{t("Épocas de Epsilon Indi B")}</button>
          </div>
        </aside>

        <div id="resultado-explorador" className="viewer" ref={results} tabIndex={-1} role="group" aria-label={t("Resultado do Explorador")}>
          {timeline ? <TimelineViewer key={timelineVersion}
            timeline={timeline} api={API}
            savedFrames={examples.find((item) => item.sequence.ra_deg === timeline.ra_deg && item.sequence.dec_deg === timeline.dec_deg)?.sequence.frames ?? []}
            onClose={closeTimeline} />
          : sequence && frame ? <section aria-label={t("Visor de comparação")} className="viewer">
            <div className="plate">
              <div className="plate-top instrument">
                <span>{example?.name ?? t("Campo consultado")}</span>
                <span>{example?.synthetic ? t("SIMULAÇÃO") : example ? t("EXEMPLO REAL") : t("IRSA · AO VIVO")}</span>
              </div>
              <div className="sky-wrap">
                <figure id="sky-field" className="sky" tabIndex={0} onKeyDown={keyboard} {...swipe} aria-label={t("Campo de comparação. Deslize na horizontal ou use as setas para alternar as épocas.")}>
                  {sequence.frames.map((image, i) => (
                    <Image key={image.frame_id} src={image.image_src} width={360} height={360} loading="eager" draggable={false}
                      alt={t("Época {index}: {date}", { index: i + 1, date: formatDate(image.observed_at_utc, locale) })}
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
                <span>{t("Época exibida")}</span>
                <input type="range" min={0} max={1} step={1} value={index}
                  aria-valuetext={formatDate(frame.observed_at_utc, locale)}
                  onChange={(event) => chooseFrame(event.currentTarget.valueAsNumber)} />
              </label>
              <div className="epochs" role="group" aria-label={t("Época exibida")}>
                {sequence.frames.map((item, i) => (
                  <button className="epoch" type="button" key={item.frame_id} aria-pressed={index === i} onClick={() => chooseFrame(i)}>
                    <span className="instrument">{t("ÉPOCA 0")}{i + 1}</span><span>{formatDate(item.observed_at_utc, locale)}</span>
                  </button>
                ))}
              </div>
              <button className="button secondary playback" type="button" onClick={() => setPlaying((previous) => !previous)}>
                <span aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span> {playing ? t("Pausar") : t("Reproduzir")}
              </button>
            </div>
            <div aria-live={playing ? "off" : "polite"} aria-atomic="true" className="sr-only">{observedLabel}: {timestamp(frame.observed_at_utc)}</div>
            {hasGuide ? (
              <div className="viewer-guide">
                <p>{t("Procure Epsilon Indi B perto do centro. Ao alternar as épocas, a fonte se desloca ligeiramente para a esquerda e para baixo em relação às estrelas do campo.")}</p>
                <button className="button secondary" type="button" aria-pressed={showGuide} aria-controls="sky-field" onClick={() => setShowGuide((visible) => !visible)}>
                  {t("Marcar região da fonte")}
                </button>
              </div>
            ) : (
              <p className="viewer-hint">{example?.synthetic ? t("Imagens simuladas. Procure o ponto que muda de posição.") : t("Confira qualquer mudança aparente nos dados de origem.")}</p>
            )}
            {exampleDescription && <details className="sources">
              <summary>{t("Descrição da comparação")}</summary>
              <p>{exampleDescription}</p>
            </details>}
            {!example && <ComparisonReadout key={sequence.sequence_id} frames={sequence.frames} />}
            <p className="viewer-hint">{t("Deslize na horizontal ou use ← → no visor para alternar.")}</p>
            <details className="sources">
              <summary>{t("Origem e processamento")}</summary>
              <dl>
                <dt>{observedLabel}</dt><dd>{timestamp(frame.observed_at_utc)}</dd>
                <dt>{t("Coleção e detector")}</dt><dd>{frame.collection} · {frame.detector}</dd>
                <dt>{example ? t("Faixa no centro") : t("Faixa do detector")}</dt><dd>{number.format(frame.wavelength_um)} µm · {t("largura")} {number.format(frame.bandwidth_um)} µm</dd>
                <dt>{t("Cobertura válida")}</dt><dd>{number.format(frame.valid_fraction * 100)}%</dd>
                {example ? <><dt>{t("Calibração")}</dt><dd>{frame.calibration_version === "Simulação" ? t("Simulação") : frame.calibration_version}</dd></> :
                  <><dt>{t("ID da observação")}</dt><dd>{frame.frame_id}</dd></>}
                <dt>{t("Recuperado em")}</dt><dd>{timestamp(sequence.fetched_at_utc)}</dd>
                <dt>{t("Processamento")}</dt><dd>{sequence.processing_version} · {timestamp(sequence.generated_at_utc)}</dd>
                {example && <><dt>{t("Produto")}</dt><dd>{source ? <a href={source} target="_blank" rel="noreferrer">{t("Exposição no IRSA ↗")}</a> : t("Sem produto de origem")}</dd></>}
                {cutout && <><dt>{t("Recorte")}</dt><dd><a href={cutout} target="_blank" rel="noreferrer">{t("Arquivo FITS ↗")}</a></dd></>}
              </dl>
            </details>
          </section> : (
            <section aria-label={t("Visor de comparação")} className="viewer" aria-busy={busy}>
              <div className="plate">
                <div className="plate-top instrument"><span>{t("Campo selecionado")}</span></div>
                <div className="sky-wrap">
                  <div className="sky timeline-placeholder">
                    <p>{busy ? t("Carregando observações…") : API
                      ? t("Busque épocas para abrir os recortes deste campo.")
                      : t("A consulta a este campo precisa de uma API configurada.")}</p>
                  </div>
                </div>
                <div className="plate-bottom instrument"><span>RA {ra}° · DEC {dec}°</span></div>
              </div>
            </section>
          )}
        </div>
      </div>
      <SpherexOrbit observedAt={timeline || example?.synthetic ? null : frame?.observed_at_utc ?? null} />
    </>
  );
}
