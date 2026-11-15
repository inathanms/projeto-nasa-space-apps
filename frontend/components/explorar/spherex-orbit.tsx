"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const EYES = "https://eyes.nasa.gov/apps/solar-system/#/sc_spherex";
const OPTIONS = "featured=false&detailPanel=false&logo=false&search=false&shareButton=false&menu=false&collapseSettingsOptions=true&locked=true&hideExternalLinks=true";
// Lançamento da SPHEREx: 12 de março de 2025, 03:10 UTC. Antes disso o Eyes não tem trajetória.
const LAUNCH = Date.parse("2025-03-12T03:10:00Z");

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" });

function eyesUrl(observedAt: string | null | undefined) {
  const time = observedAt ? Date.parse(observedAt) : NaN;
  const valid = Number.isFinite(time) && time >= LAUNCH && time <= Date.now();
  return {
    src: valid ? `${EYES}?time=${new Date(time).toISOString()}&${OPTIONS}` : `${EYES}?${OPTIONS}`,
    label: valid ? `${dateTime.format(new Date(time))} UTC` : null,
  };
}

export default function SpherexOrbit({ observedAt }: { observedAt?: string | null }) {
  const [open, setOpen] = useState(false);
  const { src: targetSrc, label: targetLabel } = eyesUrl(observedAt);
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
    <section className="orbit" id="orbita" aria-labelledby="orbit-title">
      <div className="orbit-head">
        <div>
          <p className="eyebrow instrument">NASA EYES ON THE SOLAR SYSTEM</p>
          <h2 id="orbit-title">Onde estava a SPHEREx</h2>
          <p className="muted">
            {label
              ? <>Modelo 3D da sonda na data da época exibida: <span className="instrument">{label}</span>.</>
              : "Modelo 3D da sonda em órbita da Terra, no horário atual."}
            {" "}A SPHEREx percorre uma órbita polar e varre o céu em faixas, por isso o mesmo campo é observado em datas diferentes.
          </p>
          <p className="muted orbit-alternative">
            Numa órbita polar, a sonda passa perto dos polos a cada volta. Enquanto a Terra gira, as faixas observadas cobrem diferentes partes do céu.
          </p>
          <Link className="orbit-accessible-link" href="/observatorio/">Usar o modelo de apontamento com teclado</Link>
        </div>
        <button type="button" className="button secondary" aria-expanded={open} aria-controls="orbit-frame" aria-describedby="orbit-input" onClick={() => {
          if (!open) setView({ src: targetSrc, label: targetLabel });
          setOpen(!open);
        }}>
          {open ? "Fechar visualização" : "Mostrar órbita 3D"} <span aria-hidden="true">{open ? "×" : "↗"}</span>
        </button>
      </div>
      <p className="muted" id="orbit-input">A visualização 3D da NASA usa mouse ou toque.</p>
      <div id="orbit-frame" hidden={!open}>
        {open && (
          <>
            <div className="orbit-frame">
              <iframe key={view.src} src={view.src} title="Visualização 3D interativa da sonda SPHEREx no NASA Eyes on the Solar System"
                tabIndex={-1} loading="lazy" allowFullScreen />
            </div>
            <p className="muted">
              <a href={externalUrl} target="_blank" rel="noreferrer">Abrir no site do Eyes ↗</a>
              {" "}· Crédito: NASA/JPL-Caltech.
            </p>
          </>
        )}
      </div>
    </section>
  );
}
