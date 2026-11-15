"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { Target } from "../../lib/pointing";
import { formatDate } from "../../lib/sequence";
import { fetchEpochs, fetchExposure, SpherexApiError } from "../../lib/spherex-api";
import { useLocale } from "../ui/LocaleProvider";
import RocketLoader from "../ui/RocketLoader";

const SETTLE_MS = 500;
const HEALTH_TTL_MS = 30_000;
const OFFLINE_RETRY_MS = 20_000;

type Preview =
  | { status: "waiting" | "loading" | "offline" | "empty" | "error" }
  | { status: "ready"; src: string; caption: string };

// Cache da visita: o mesmo ponto não é buscado duas vezes, e a saúde da API é checada no máximo a cada 30 s.
const images = new Map<string, { src: string; observedAt: string } | null>();
let health: { ok: boolean; at: number } | null = null;

async function apiOnline(api: string, force = false) {
  if (!force && health && Date.now() - health.at < HEALTH_TTL_MS) return health.ok;
  let ok = false;
  try {
    const response = await fetch(`${api}/health`, { signal: AbortSignal.timeout(6_000), cache: "no-store" });
    ok = response.ok;
  } catch { /* Sem resposta: API desligada ou inacessível. */ }
  health = { ok, at: Date.now() };
  return ok;
}

/** Erros de rede e 5xx do próprio serviço contam como "API desligada"; os demais, como falha da consulta. */
function looksOffline(error: unknown) {
  if (error instanceof SpherexApiError) return error.status === 503 || error.status === 502 && error.code === "HTTP_ERROR";
  return error instanceof TypeError || error instanceof DOMException && error.name === "TimeoutError";
}

/** Preview da região apontada, mostrada no diário de bordo depois que a mira para por 0,5 s. */
export default function PointingPreview({ api, ra, dec, target, paused, importHref }: {
  api?: string;
  ra: number;
  dec: number;
  /** Alvo configurado exatamente sob a mira: usa a imagem salva no site, sem depender da API. */
  target: Target | null;
  paused: boolean;
  importHref: string;
}) {
  const { t, locale } = useLocale();
  const [preview, setPreview] = useState<Preview>({ status: "waiting" });
  const [retry, setRetry] = useState(0);
  const forceHealth = useRef(false);
  const tryAgain = () => {
    forceHealth.current = true;
    setRetry((value) => value + 1);
  };

  useEffect(() => {
    setPreview({ status: "waiting" });
    if (paused) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      if (target?.preview) {
        setPreview({ status: "ready", src: target.preview, caption: t("Imagem salva de {name}", { name: target.name }) });
        return;
      }
      const force = forceHealth.current;
      forceHealth.current = false;
      if (!api || !(await apiOnline(api, force))) {
        if (!controller.signal.aborted) setPreview({ status: "offline" });
        return;
      }
      const key = `${ra.toFixed(3)},${dec.toFixed(3)}`;
      try {
        let image = images.get(key);
        if (image === undefined) {
          setPreview({ status: "loading" });
          const timeline = await fetchEpochs(api, ra, dec, controller.signal);
          // Detector único (mesma visualização padrão do Explorador).
          const first = timeline.exposures[0];
          if (first) {
            const { frame } = await fetchExposure(api, timeline, first, controller.signal);
            image = { src: frame.image_src, observedAt: frame.observed_at_utc };
          } else {
            image = null;
          }
          images.set(key, image);
        }
        if (controller.signal.aborted) return;
        setPreview(image
          ? { status: "ready", src: image.src, caption: t("Observação SPHEREx · {date}", { date: formatDate(image.observedAt, locale) }) }
          : { status: "empty" });
      } catch (error) {
        if (controller.signal.aborted) return;
        if (looksOffline(error)) health = { ok: false, at: Date.now() };
        setPreview({ status: looksOffline(error) ? "offline" : "error" });
      }
    }, SETTLE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [api, ra, dec, target, paused, retry, t, locale]);

  // Com a API desligada, confere de tempos em tempos e mostra a imagem assim que ela voltar.
  useEffect(() => {
    if (preview.status !== "offline" || !api) return;
    const timer = window.setInterval(async () => {
      if (await apiOnline(api, true)) setRetry((value) => value + 1); // health já atualizado: não força de novo
    }, OFFLINE_RETRY_MS);
    return () => window.clearInterval(timer);
  }, [preview.status, api]);

  return (
    <figure className="orbital-preview" data-status={preview.status} aria-busy={preview.status === "loading"}>
      <div className="orbital-preview-frame">
        {preview.status === "ready"
          // <img> simples: a fonte é um arquivo local ou um data: URL vindo da API.
          ? <img src={preview.src} alt={t("Prévia da região apontada pelo telescópio")} />
          : <div className="orbital-preview-state" role="status">
            {preview.status === "waiting" && <p>{paused ? t("Preview pausada durante a reprodução do tempo.") : t("Aguardando a mira parar…")}</p>}
            {preview.status === "loading" && <RocketLoader label={t("Buscando imagem do SPHEREx…")} />}
            {preview.status === "offline" && <>
              <p><strong><span className="orbital-preview-dot" aria-hidden="true" /> {t("API desligada no momento")}</strong></p>
              <p>{t("A preview de regiões fora dos alvos configurados depende da API. Quando ela voltar, a imagem aparece aqui.")}</p>
              <button type="button" className="orbital-preview-retry" onClick={tryAgain}>{t("Tentar de novo")}</button>
            </>}
            {preview.status === "empty" && <p>{t("O SPHEREx ainda não observou esta região.")}</p>}
            {preview.status === "error" && <>
              <p>{t("Não foi possível carregar a preview desta região.")}</p>
              <button type="button" className="orbital-preview-retry" onClick={tryAgain}>{t("Tentar de novo")}</button>
            </>}
          </div>}
      </div>
      {preview.status === "ready" && <figcaption>{preview.caption}</figcaption>}
      <Link className="button primary orbital-preview-import" href={importHref}>{t("Importar para o explorador")}</Link>
    </figure>
  );
}
