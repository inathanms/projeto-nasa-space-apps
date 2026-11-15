"use client";

import { useLocale } from "../ui/LocaleProvider";
import { forLocales } from "../../lib/i18n";

import dynamic from "next/dynamic";
import Image from "next/image";
import Help from "../ui/Help";
import { setDiscoveryField } from "../../lib/discovery";
import { useEffect, useEffectEvent, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { formatDate, sourceLink, type Example, type Sequence } from "../../lib/sequence";
import { isTimeline, type CatalogExposure, type LiveTimeline, type Timeline } from "../../lib/timeline";
import { exampleAliases, exampleDescriptions } from "../../content/examples";
import { apiErrorMessage, fetchComparison, fetchEpochs, fetchRgbFrame } from "../../lib/spherex-api";
import { parseCoordinate } from "../../lib/coordinates";
import ComparisonReadout from "./comparison-readout";
import ImageFormat, { type ImageMode } from "./image-format";
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

const numbers = forLocales((language) => new Intl.NumberFormat(language, { maximumFractionDigits: 5 }));
const dateTimes = forLocales((language) => new Intl.DateTimeFormat(language, {
  dateStyle: "medium", timeStyle: "medium", timeZone: "UTC",
}));

export default function Explorer({ examples, api }: { examples: [Example, ...Example[]]; api?: string }) {
  const { t, locale } = useLocale();
  const number = numbers[locale];
  const dateTime = dateTimes[locale];
  const timestamp = (date: string | null) =>
    date && Number.isFinite(Date.parse(date)) ? dateTime.format(new Date(date)) + " UTC" : "—";
  const [example, setExample] = useState<Example | null>(examples[0]);
  const [sequence, setSequence] = useState<Sequence | null>(examples[0].sequence);
  const [selected, setSelected] = useState("");
  const [ra, setRa] = useState(String(examples[0].sequence.ra_deg));
  const [dec, setDec] = useState(String(examples[0].sequence.dec_deg));
  const [index, setIndex] = useState(0);
  const [rgbSource, setRgbSource] = useState<{ timeline: LiveTimeline; exposures: CatalogExposure[] }>();
  const [rgbLoading, setRgbLoading] = useState(false);
  const [rgbError, setRgbError] = useState("");
  const [mode, setMode] = useState<ImageMode>("single");
  const [playing, setPlaying] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [timelineVersion, setTimelineVersion] = useState(0);
  const [invalid, setInvalid] = useState<"ra" | "dec" | "">("");
  const rgbRequest = useRef<AbortController | null>(null);
  const active = useRef<AbortController | null>(null);
  const results = useRef<HTMLDivElement>(null);
  const revealFrom = useRef<HTMLElement | null>(null);
  const timelineTrigger = useRef<HTMLElement | null>(null);
  const raInput = useRef<HTMLInputElement>(null);
  const decInput = useRef<HTMLInputElement>(null);
  const rgbFrames = sequence?.rgb_frames;
  const frames = (mode === "rgb" ? rgbFrames : undefined) ?? sequence?.frames;
  const frame = frames?.[index];
  const frameCount = frames?.length ?? 0;
  const canCompare = frameCount > 1;
  const epsilon = examples.find((item) => item.slug === "eps-indi-b");
  const timelineTarget = timeline && examples.find(({ sequence, synthetic }) =>
    !synthetic && sequence.ra_deg === timeline.ra_deg && sequence.dec_deg === timeline.dec_deg);
  const canUseRgb = Boolean(rgbFrames || (rgbSource && rgbSource.exposures.length > 0));
  const guideName = example && !example.synthetic ? example.name : undefined;

  useEffect(() => {
    if (timeline) return;
    setDiscoveryField(sequence && !example?.synthetic ? {
      name: example?.name,
      ra: sequence.ra_deg,
      dec: sequence.dec_deg,
      times: frames?.map((item) => item.observed_at_utc) ?? [],
    } : null);
  }, [example, frames, sequence, timeline]);
  useEffect(() => () => setDiscoveryField(null), []);

  const openLinkedField = useEffectEvent(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedSlug = params.get("exemplo") ?? params.get("alvo") ?? "";
    const slug = exampleAliases[requestedSlug] ?? requestedSlug;
    const requestedRA = parseCoordinate(params.get("ra_deg") ?? "");
    const requestedDec = parseCoordinate(params.get("dec_deg") ?? "");
    const hasField = requestedRA >= 0 && requestedRA < 360 && requestedDec >= -90 && requestedDec <= 90;
    const mode = params.get("modo");
    if (mode === "epocas" && !hasField && epsilon) {
      openTargetTimeline(epsilon);
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
      rgbRequest.current?.abort();
      active.current?.abort();
      active.current = null;
    };
  }, [examples]);

  useEffect(() => {
    if (!playing || !canCompare) return;
    const timer = window.setInterval(() => setIndex((previous) => (previous + 1) % frameCount), 900);
    return () => window.clearInterval(timer);
  }, [playing, canCompare, frameCount]);

  useEffect(() => {
    if (revealFrom.current && document.activeElement === revealFrom.current) results.current?.focus();
    revealFrom.current = null;
  }, [sequence, timeline]);

  function applyExample(preset: Example, trigger?: HTMLElement) {
    active.current?.abort();
    resetRgb();
    active.current = null;
    revealFrom.current = trigger ?? null;
    setBusy(false);
    setPlaying(false);
    setShowGuide(false);
    setIndex(0);
    setMode("single");
    setError("");
    setInvalid("");
    setSelected(preset.preset ? preset.slug : "");
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

  function openTargetTimeline(target: Example, trigger?: HTMLElement) {
    if (active.current) return;
    const { ra_deg, dec_deg } = target.sequence;
    setRa(String(ra_deg));
    setDec(String(dec_deg));
    void requestField(ra_deg, dec_deg, true, trigger);
  }

  async function requestField(r: number, d: number, catalog: boolean, trigger?: HTMLElement) {
    const savedEpsilon = catalog && r === epsilon?.sequence.ra_deg && d === epsilon.sequence.dec_deg;
    if (!api && !savedEpsilon) {
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
      let epochs: LiveTimeline | undefined;
      if (api) {
        const catalogSignal = savedEpsilon
          ? AbortSignal.any([request.signal, AbortSignal.timeout(12_000)])
          : request.signal;
        try {
          epochs = await fetchEpochs(api, r, d, catalogSignal);
        } catch (cause) {
          if (!savedEpsilon) throw cause;
          request.signal.throwIfAborted();
        }
      }
      if (active.current !== request) return;

      if (catalog) {
        let data: Timeline | undefined = epochs;
        if (savedEpsilon && !epochs?.exposures.length) {
          const response = await fetch("/examples/eps-indi-b/timeline.json", { signal: request.signal });
          const payload: unknown = await response.json();
          if (!response.ok || !isTimeline(payload)) {
            setError(t("Não foi possível abrir o catálogo salvo."));
            return;
          }
          data = payload;
        }
        if (!data || active.current !== request) return;
        revealFrom.current = trigger ?? null;
        timelineTrigger.current = trigger ?? null;
        setTimeline(data);
        setTimelineVersion((version) => version + 1);
      } else if (api && epochs) {
        const pair = await fetchComparison(api, epochs, request.signal, locale);
        request.signal.throwIfAborted();
        if (active.current !== request) return;
        revealFrom.current = trigger ?? null;
        resetRgb();
        setRgbSource({ timeline: epochs, exposures: pair.rgbExposures });
        setTimeline(null);
        setSequence(pair.sequence);
        setExample(null);
        setShowGuide(false);
        setIndex(0);
        setMode("single");
      }
    } catch (cause) {
      if (active.current === request) setError(apiErrorMessage(cause, locale));
    } finally {
      window.clearTimeout(timeout);
      if (active.current === request) {
        active.current = null;
        setBusy(false);
      }
    }
  }

  function resetRgb() {
    rgbRequest.current?.abort();
    rgbRequest.current = null;
    setRgbSource(undefined);
    setRgbLoading(false);
    setRgbError("");
  }

  async function changeFormat(next: ImageMode) {
    setRgbError("");
    if (next === "single" || rgbFrames) {
      setMode(next);
      chooseFrame(0);
      return;
    }
    if (!api || !sequence || !rgbSource?.exposures.length || rgbRequest.current) return;
    const request = new AbortController();
    rgbRequest.current = request;
    setPlaying(false);
    setRgbLoading(true);
    try {
      const results = await Promise.allSettled(rgbSource.exposures.map((item) => fetchRgbFrame(api, rgbSource.timeline, item, request.signal)));
      if (rgbRequest.current !== request) return;
      const [first, ...rest] = results.flatMap((result) => result.status === "fulfilled" ? [result.value] : []);
      if (!first) {
        const failed = results.find((result) => result.status === "rejected");
        throw failed?.reason;
      }
      setSequence({ ...sequence, rgb_frames: [first, ...rest] });
      setMode("rgb");
      chooseFrame(0);
    } catch (cause) {
      if (rgbRequest.current === request) setRgbError(apiErrorMessage(cause, locale));
    } finally {
      if (rgbRequest.current === request) {
        request.abort();
        rgbRequest.current = null;
        setRgbLoading(false);
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

  function moveFrame(direction: -1 | 1) {
    if (canCompare) chooseFrame((index + frameCount + direction) % frameCount);
  }

  function keyboard(event: KeyboardEvent<HTMLElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    moveFrame(event.key === "ArrowLeft" ? -1 : 1);
  }

  const swipe = useSkySwipe(moveFrame);
  const observedLabel = example?.synthetic ? t("Data ilustrativa") : t("Observação");
  const source = sourceLink(frame?.source_url ?? null);
  const cutout = sourceLink(frame?.cutout_url ?? null);
  const exampleDescription = example && exampleDescriptions(locale)[example.slug];
  const presets = examples.filter((item) => item.preset);
  const selectedPreset = presets.find((item) => item.slug === selected);

  return (
    <>
      <div className="explorer-grid">
        <aside className="controls" aria-label={t("Escolha do campo")}>
          <div className="preset" data-tour="explorar-exemplos">
            <h2>{t("Alvos offline")}</h2>
            <p className="muted offline-note">{t("Abra um alvo com imagens salvas no site, mesmo quando a API estiver indisponível.")}</p>
            <label htmlFor="preset">{t("Campo de observação")}</label>
            <select className="control-field" id="preset" value={selected} onChange={(event) => setSelected(event.target.value)}>
              <option value="" disabled>{t("Escolha um alvo")}</option>
              <optgroup label={t("Alvos pré-configurados do SPHEREx")}>
                {presets.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}
              </optgroup>
            </select>
            <button type="button" className="button secondary" disabled={!selectedPreset} aria-controls="resultado-explorador"
              onClick={(event) => { if (selectedPreset) applyExample(selectedPreset, event.currentTarget); }}>{t("Abrir exemplo")} <span aria-hidden="true">↗</span></button>
            {api && selectedPreset && <button type="button" className="button secondary" aria-disabled={busy} aria-controls="resultado-explorador"
              onClick={(event) => openTargetTimeline(selectedPreset, event.currentTarget)}>
              {t("Todas as épocas de {name}", { name: selectedPreset.name })}
            </button>}
          </div>
          <form data-tour="explorar-busca" onSubmit={(event) => void search(event, (event.nativeEvent as SubmitEvent).submitter?.id !== "compare-pair")} noValidate>
            <h2>{t("Buscar por coordenadas")}</h2>
            <p className="muted" id="coordinate-format">{t("Use graus decimais no sistema ICRS.")}<Help id="icrs" label={t("o sistema ICRS")} /></p>
            <div className="label-row"><label htmlFor="ra">{t("Ascensão reta")} <span>RA</span></label><Help id="ascensao-reta" label={t("ascensão reta")} /></div>
            <input className="control-field" ref={raInput} id="ra" name="ra_deg" inputMode="decimal" value={ra} readOnly={busy} onChange={(event) => {
              setRa(event.target.value);
              if (invalid === "ra") {
                setInvalid("");
                setError("");
              }
            }} aria-invalid={invalid === "ra"} aria-describedby={invalid === "ra" ? "coordinate-format search-error" : "coordinate-format"} />
            <div className="label-row"><label htmlFor="dec">{t("Declinação")} <span>DEC</span></label><Help id="declinacao" label={t("declinação")} /></div>
            <input className="control-field" ref={decInput} id="dec" name="dec_deg" inputMode="decimal" value={dec} readOnly={busy} onChange={(event) => {
              setDec(event.target.value);
              if (invalid === "dec") {
                setInvalid("");
                setError("");
              }
            }} aria-invalid={invalid === "dec"} aria-describedby={invalid === "dec" ? "coordinate-format search-error" : "coordinate-format"} />
            <button className="button primary" type="submit" aria-disabled={busy} aria-controls="resultado-explorador">{t("Buscar épocas no IRSA")}<span aria-hidden="true">↗</span></button>
            {api && <button id="compare-pair" className="button secondary" type="submit" aria-disabled={busy}
              aria-controls="resultado-explorador">{t("Buscar par para comparação")}</button>}
            {!api && <p className="muted offline-note">{t("A busca ao vivo requer uma API configurada neste ambiente.")}</p>}
            <p role="status" className="muted search-feedback">{busy ? t("Carregando observações…") : ""}</p>
            <p id="search-error" className="error search-feedback" role="alert">{error}</p>
          </form>
        </aside>

        <div id="resultado-explorador" className="viewer" ref={results} tabIndex={-1} role="group" aria-label={t("Resultado do Explorador")}>
          {timeline ? <TimelineViewer key={timelineVersion}
            timeline={timeline} api={timeline.source === "live" ? api : undefined}
            targetName={timelineTarget?.name}
            savedFrames={timeline.source === "live" ? [] : epsilon?.sequence.frames ?? []}
            onClose={closeTimeline} />
          : sequence && frames && frame ? <section aria-label={t("Visor de comparação")} className="viewer">
            <div className="plate" data-tour="explorar-visor">
              <div className="plate-top instrument">
                <span className="plate-name">{example?.name ?? t("Campo consultado")}</span>
                <span>{example?.synthetic ? t("SIMULAÇÃO") : example ? t("EXEMPLO REAL") : t("IRSA · AO VIVO")}</span>
              </div>
              <div className="sky-wrap">
                <figure id="sky-field" className={mode === "single" && !example?.synthetic ? "sky sky-grayscale" : "sky"} tabIndex={canCompare ? 0 : undefined}
                  {...(canCompare ? { onKeyDown: keyboard, ...swipe } : {})}
                  aria-label={canCompare ? t("Campo de comparação. Deslize na horizontal ou use as setas para alternar as épocas.") : t("Campo de observação")}>
                  {frames.map((image, i) => (
                    <Image key={image.frame_id} src={image.image_src} width={360} height={360} loading="eager" draggable={false}
                      alt={t("Época {index}: {date}", { index: i + 1, date: formatDate(image.observed_at_utc, locale) })}
                      className={index === i ? "" : "hidden-frame"} aria-hidden={index !== i} />
                  ))}
                  <span className="north instrument" aria-hidden="true">N ↑<br />E ←</span>
                  <span className="scale instrument" aria-hidden="true">{number.format(sequence.fov_arcmin / 6)}′</span>
                  {showGuide && <span className="sky-guide" aria-hidden="true" />}
                </figure>
              </div>
              <div className="plate-bottom instrument">
                <span>RA {number.format(sequence.ra_deg)}° · DEC {number.format(sequence.dec_deg)}°</span>
                <span>{number.format(sequence.fov_arcmin)}′ × {number.format(sequence.fov_arcmin)}′</span>
              </div>
            </div>

            <div className="viewer-tools" data-tour="explorar-marcar">
              {!example?.synthetic && <ImageFormat mode={mode} rgbAvailable={canUseRgb} busy={rgbLoading} onChange={(next) => void changeFormat(next)} />}
              <button className="button secondary mark-target" type="button" aria-pressed={showGuide} aria-controls="sky-field" onClick={() => setShowGuide((visible) => !visible)}>
                {guideName ? t("Marcar {name}", { name: guideName }) : t("Marcar alvo")}
              </button>
            </div>
            {rgbLoading && <p className="viewer-hint" role="status">{t("Carregando composição RGB…")}</p>}
            {rgbError && <p className="error" role="alert">{rgbError}</p>}
            {canCompare ? <div className="transport" data-tour="explorar-epocas">
              <label className="epoch-range">
                <span>{t("Época exibida")}</span>
                <input type="range" min={0} max={frameCount - 1} step={1} value={index}
                  aria-valuetext={formatDate(frame.observed_at_utc, locale)}
                  onChange={(event) => chooseFrame(event.currentTarget.valueAsNumber)} />
              </label>
              <div className="epochs" role="group" aria-label={t("Época exibida")}>
                {frames.map((item, i) => (
                  <button className="epoch" type="button" key={item.frame_id} aria-pressed={index === i} onClick={() => chooseFrame(i)}>
                    <span className="instrument">{t("ÉPOCA {index}", { index: String(i + 1).padStart(2, "0") })}</span><span>{formatDate(item.observed_at_utc, locale)}</span>
                  </button>
                ))}
              </div>
              <button className="button secondary playback" type="button" onClick={() => setPlaying((previous) => !previous)}>
                <span aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span> {playing ? t("Pausar") : t("Reproduzir")}
              </button>
            </div> : <p className="viewer-hint">
              {observedLabel}: {formatDate(frame.observed_at_utc, locale)}. {t("Este formato tem uma única época disponível.")}
            </p>}
            {(example?.preset || !example) && canCompare && <p className="viewer-hint">{mode === "rgb"
              ? t("As composições RGB usam escalas de brilho próprias.")
              : t("As imagens em tons de cinza usam a mesma escala de brilho entre épocas.")}</p>}
            <div aria-live={playing ? "off" : "polite"} aria-atomic="true" className="sr-only">{observedLabel}: {timestamp(frame.observed_at_utc)}</div>
            {example?.slug === "eps-indi-b" && canCompare && <p className="viewer-hint">
              {t("Procure Epsilon Indi B perto do centro. Ao alternar as épocas, a fonte se desloca ligeiramente para a esquerda e para baixo em relação às estrelas do campo.")}
            </p>}
            {example?.synthetic && <p className="viewer-hint">{t("Imagens simuladas. Procure o ponto que muda de posição.")}</p>}
            {exampleDescription && <details className="sources">
              <summary>{t("Descrição da comparação")}</summary>
              <p>{exampleDescription}</p>
            </details>}
            {!example && mode === "single" && frames[1] && <ComparisonReadout key={sequence.sequence_id} frames={[frames[0], frames[1]]} />}
            {canCompare && <p className="viewer-hint">{t("Deslize na horizontal ou use ← → no visor para alternar.")}<Help id="epoca" label={t("uma época")} /></p>}
            <details className="sources" data-tour="explorar-origem">
              <summary>{t("Origem e processamento")}</summary>
              <dl>
                <dt>{observedLabel}</dt><dd>{timestamp(frame.observed_at_utc)}</dd>
                <dt>{t("Coleção e detector")}</dt><dd>{frame.collection} · {frame.detector}</dd>
                <dt>{frame.wavelength_bands_um ? t("Bandas RGB") : example && !example.preset ? t("Faixa no centro") : t("Faixa do detector")}<Help id="comprimento-de-onda" label={t("a faixa de comprimento de onda")} /></dt>
                <dd>{frame.wavelength_bands_um?.map(([min, max], i) => `${"RGB"[i]} ${number.format(min)}–${number.format(max)} µm`).join(" · ") ??
                  <>{number.format(frame.wavelength_um)} µm · {t("largura")} {number.format(frame.bandwidth_um)} µm</>}</dd>
                {frame.valid_fraction !== null && <><dt>{t("Cobertura válida")}</dt><dd>{number.format(frame.valid_fraction * 100)}%</dd></>}
                {example && !example.preset ? <><dt>{t("Calibração")}</dt><dd>{frame.calibration_version === "Simulação" ? t("Simulação") : frame.calibration_version}</dd></> :
                  <><dt>{t("ID da observação")}</dt><dd>{frame.frame_id}</dd></>}
                <dt>{t("Recuperado em")}</dt><dd>{timestamp(sequence.fetched_at_utc)}</dd>
                <dt>{t("Processamento")}</dt><dd>{sequence.processing_version} · {timestamp(sequence.generated_at_utc)}</dd>
                {example && !example.preset && <><dt>{t("Produto")}</dt><dd>{source ? <a href={source} target="_blank" rel="noreferrer">{t("Exposição no IRSA ↗")}</a> : t("Sem produto de origem")}</dd></>}
                {cutout && <><dt>{t("Recorte")}<Help id="fits" label={t("um arquivo FITS")} /></dt><dd><a href={cutout} target="_blank" rel="noreferrer">{t("Arquivo FITS ↗")}</a></dd></>}
              </dl>
            </details>
          </section> : (
            <section aria-label={t("Visor de comparação")} className="viewer" aria-busy={busy}>
              <div className="plate">
                <div className="plate-top instrument"><span>{t("Campo selecionado")}</span></div>
                <div className="sky-wrap">
                  <div className="sky timeline-placeholder">
                    <p>{busy ? t("Carregando observações…") : api
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
