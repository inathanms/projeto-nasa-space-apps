"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { presetFacts, targetInfo } from "../../content/target-info";
import { forLocales } from "../../lib/i18n";
import type { Target } from "../../lib/pointing";
import { formatDate } from "../../lib/sequence";
import { useLocale } from "../ui/LocaleProvider";

const angles = forLocales((language) => new Intl.NumberFormat(language, { maximumFractionDigits: 6 }));

/** Ficha do astro exibida junto ao diário de bordo. */
export default function TargetSheet({ target, focusOnOpen, onClose }: {
  target: Target | null;
  focusOnOpen: boolean;
  onClose: () => void;
}) {
  const { locale, t, href } = useLocale();
  const closeButton = useRef<HTMLButtonElement>(null);
  const info = target ? targetInfo[locale][target.slug.replace(/^preset-/, "")] : undefined;
  const preset = target ? presetFacts[target.slug] : undefined;
  const kind = info?.tipo ?? preset?.kind[locale];
  const note = info?.oQueVer ?? preset?.note?.[locale];

  useEffect(() => {
    if (target && focusOnOpen) closeButton.current?.focus();
  }, [target, focusOnOpen]);

  if (!target) return null;

  return (
    <section id="target-sheet" className="target-sheet" aria-labelledby="target-sheet-title"
      onKeyDown={(event) => {
        if (event.key !== "Escape") return;
        event.stopPropagation();
        onClose();
      }}>
      <div className="target-sheet-body">
        <header className="target-sheet-head">
          <div>
            {kind && <p className="target-sheet-kicker">{kind}</p>}
            <h2 id="target-sheet-title">{target.name}</h2>
          </div>
          <button ref={closeButton} type="button" className="target-sheet-close" aria-label={t("Fechar ficha")} onClick={onClose}>×</button>
        </header>

        <dl className="target-sheet-facts">
          {preset && <div><dt>{t("Identificação no catálogo")}</dt><dd>{preset.catalog}</dd></div>}
          <div><dt>{t("Coordenadas celestes")}</dt><dd>RA {angles[locale].format(target.ra)}° · Dec {angles[locale].format(target.dec)}°</dd></div>
          <div><dt>{t("Observação UTC")}</dt><dd><time dateTime={target.time}>{formatDate(target.time, locale)} · {target.time.slice(11, 19)}</time></dd></div>
          {info && <div><dt>{t("Constelação")}</dt><dd>{info.constelacao}</dd></div>}
          {info?.distancia && <div><dt>{t("Distância")}</dt><dd>{info.distancia}</dd></div>}
          {info?.descoberta && <div><dt>{t("Descoberta")}</dt><dd>{info.descoberta.quem} · {info.descoberta.quando}</dd></div>}
        </dl>

        {info?.descoberta && <section>
          <h3>{t("Como foi descoberto")}</h3>
          <p>{info.descoberta.como}</p>
        </section>}
        {info && <section>
          <h3>{t("Contexto histórico")}</h3>
          <p>{info.historia}</p>
        </section>}
        {info?.curiosidades?.length ? <section>
          <h3>{info.curiosidades.length > 1 ? t("Curiosidades") : t("Curiosidade")}</h3>
          {info.curiosidades.length > 1
            ? <ul>{info.curiosidades.map((fact) => <li key={fact}>{fact}</li>)}</ul>
            : <p>{info.curiosidades[0]}</p>}
        </section> : null}
        {note && <p className="target-sheet-look"><strong>{t("O que observar nas imagens:")}</strong> {note}</p>}
        <Link className="button secondary" href={href(`/explorar/?exemplo=${encodeURIComponent(target.slug)}`)}>
          {t("Abrir imagens no Explorador")}
        </Link>
      </div>
    </section>
  );
}
