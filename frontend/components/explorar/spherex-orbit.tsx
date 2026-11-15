"use client";

import { useLocale } from "../ui/LocaleProvider";
import { forLocales, type Locale } from "../../lib/i18n";

import { useEffect, useState } from "react";
import Link from "next/link";
import Help from "../ui/Help";

const EYES = "https://eyes.nasa.gov/apps/solar-system/#/sc_spherex";
// rate=0 congela o relógio do Eyes: a sonda fica parada na data pedida em vez de seguir em tempo real.
const OPTIONS = "rate=0&featured=false&detailPanel=false&logo=false&search=false&shareButton=false&menu=false&collapseSettingsOptions=true&locked=true&hideExternalLinks=true";
// Lançamento da SPHEREx: 12 de março de 2025, 03:10 UTC. Antes disso o Eyes não tem trajetória.
const LAUNCH = Date.parse("2025-03-12T03:10:00Z");

const dateTimes = forLocales((language) => new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }));

function eyesUrl(observedAt: string | null | undefined, locale: Locale) {
  const dateTime = dateTimes[locale];
  const time = observedAt ? Date.parse(observedAt) : NaN;
  const valid = Number.isFinite(time) && time >= LAUNCH && time <= Date.now();
  return {
    src: valid ? `${EYES}?time=${new Date(time).toISOString()}&${OPTIONS}` : `${EYES}?${OPTIONS}`,
    label: valid ? `${dateTime.format(new Date(time))} UTC` : null,
  };
}

export default function SpherexOrbit({ observedAt }: { observedAt?: string | null }) {
  const { t, locale, href } = useLocale();
  const [open, setOpen] = useState(false);
  const { src: targetSrc, label: targetLabel } = eyesUrl(observedAt, locale);
  // Espera a época ficar estável (ex.: durante a reprodução) antes de recarregar o Eyes.
  const [view, setView] = useState({ src: targetSrc, label: targetLabel });
  useEffect(() => {
    if (!open || targetSrc === view.src) return;
    const timer = window.setTimeout(() => setView({ src: targetSrc, label: targetLabel }), 1500);
    return () => window.clearTimeout(timer);
  }, [open, targetSrc, targetLabel, view.src]);
  const label = open ? view.label : targetLabel;
  const externalUrl = view.label ? `${EYES}?${view.src.split("?")[1].split("&")[0]}` : EYES;

  return (
    <section className="orbit" id="orbita" data-tour="explorar-orbita" aria-labelledby="orbit-title">
      <div className="orbit-head">
        <div>
          <p className="eyebrow instrument">NASA EYES ON THE SOLAR SYSTEM</p>
          <h2 id="orbit-title">{t("Onde estava a SPHEREx")}</h2>
          <p className="muted">
            {label
              ? <>{t("Modelo 3D da sonda na data da época exibida:")} <span className="instrument">{label}</span>.</>
              : t("Modelo 3D da sonda em órbita da Terra, no horário atual.")}
            {" "}{t("A SPHEREx percorre uma órbita polar e varre o céu em faixas, por isso o mesmo campo é observado em datas diferentes.")}
            <Help id="orbita-polar" label={t("órbita polar")} />
          </p>
          <p className="muted orbit-alternative">
            {t("Numa órbita polar, a sonda passa perto dos polos a cada volta. Enquanto a Terra gira, as faixas observadas cobrem diferentes partes do céu.")}
          </p>
          <Link className="orbit-accessible-link" href={href("/observatorio/")}>{t("Usar o modelo de apontamento com teclado")}</Link>
        </div>
        <button type="button" className="button secondary" aria-expanded={open} aria-controls="orbit-frame" aria-describedby="orbit-input" onClick={() => {
          if (!open) setView({ src: targetSrc, label: targetLabel });
          setOpen(!open);
        }}>
          {open ? t("Fechar visualização") : t("Mostrar órbita 3D")} <span aria-hidden="true">{open ? "×" : "↗"}</span>
        </button>
      </div>
      <p className="muted" id="orbit-input">{t("A visualização 3D da NASA usa mouse ou toque.")}</p>
      <div id="orbit-frame" hidden={!open}>
        {open && (
          <>
            <div className="orbit-frame">
              <iframe key={view.src} src={view.src} title={t("Visualização 3D interativa da sonda SPHEREx no NASA Eyes on the Solar System")}
                tabIndex={-1} loading="lazy" allowFullScreen />
            </div>
            <p className="muted">
              <a href={externalUrl} target="_blank" rel="noreferrer">{t("Abrir no site do Eyes ↗")}</a>
              {t(" · Crédito: NASA/JPL-Caltech.")}
            </p>
          </>
        )}
      </div>
    </section>
  );
}
