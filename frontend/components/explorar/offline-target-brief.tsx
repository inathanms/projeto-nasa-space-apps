import Image from "next/image";
import { useState } from "react";
import { offlineTargetBriefs } from "../../content/offline-targets";
import { formatDate, type Example } from "../../lib/sequence";
import { useLocale } from "../ui/LocaleProvider";

export default function OfflineTargetBrief({ example }: { example: Example }) {
  const { locale, t } = useLocale();
  const [showPair, setShowPair] = useState(false);
  const brief = offlineTargetBriefs[example.slug];
  if (!brief) return null;

  const copy = brief[locale];
  const { frames, rgb_frames: rgbFrames } = example.sequence;
  const first = frames[0];
  const last = frames.length > 1 ? frames.at(-1) : undefined;
  const second = last ?? rgbFrames?.[0];
  const sharedDetector = last && first.detector === last.detector;
  const cutouts = second ? [first, second] : [];

  return (
    <section className="offline-brief" aria-labelledby="offline-brief-title">
      <h2 id="offline-brief-title">{t("Sobre o alvo")}</h2>
      <p>{copy.description}</p>
      <h3>{t("O que comparar")}</h3>
      <p>{copy.comparison}</p>
      {second && <details className="offline-comparison" onToggle={(event) => setShowPair(event.currentTarget.open)}>
        <summary>{t("Comparar recortes lado a lado")}</summary>
        <p>{sharedDetector
          ? t("Primeira e última época do mesmo detector, com a mesma escala de brilho. Compare somente a área observada nos dois recortes.")
          : t("Os formatos usam bandas e escalas de brilho diferentes. Compare as estruturas na área em comum.")}</p>
        {showPair && <div className="offline-pair">
          {cutouts.map((frame, index) => {
            const format = frame.wavelength_bands_um ? t("Composição RGB") : t("Detector único");
            const date = formatDate(frame.observed_at_utc, locale);
            return (
              <figure key={frame.image_src}>
                <Image src={frame.image_src} width={360} height={360} loading="lazy"
                  alt={t("{name} em {date} · {format}", { name: example.name, date, format })} />
                <figcaption>
                  <strong>{last ? t(index === 0 ? "Primeira época" : "Última época") : format}</strong>
                  <span><time dateTime={frame.observed_at_utc}>{date}</time> · {frame.detector}</span>
                </figcaption>
              </figure>
            );
          })}
        </div>}
      </details>}
      <h3>{t("Curiosidade")}</h3>
      <p>{copy.fact}</p>
      <a className="offline-reference" href={brief.source.href} target="_blank" rel="noreferrer">
        {t("Fonte: {name}", { name: brief.source.name })} <span aria-hidden="true">↗</span>
      </a>
    </section>
  );
}
