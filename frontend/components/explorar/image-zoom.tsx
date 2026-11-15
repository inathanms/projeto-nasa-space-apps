import { useLocale } from "../ui/LocaleProvider";
import { forLocales } from "../../lib/i18n";

const scales = forLocales((language) => new Intl.NumberFormat(language, { maximumFractionDigits: 2 }));

export default function ImageZoom({ zoom, onStep, controls }: {
  zoom: number;
  onStep: (amount: number) => void;
  controls: string;
}) {
  const { t, locale } = useLocale();
  return (
    <div className="image-zoom" role="group" aria-label={t("Zoom da imagem")}>
      <button className="button secondary" type="button" aria-label={t("Reduzir zoom")}
        aria-controls={controls} aria-disabled={zoom <= 1} onClick={() => { if (zoom > 1) onStep(-1); }}>−</button>
      <output aria-label={t("Zoom da imagem")} aria-live="off">{scales[locale].format(zoom)}×</output>
      <button className="button secondary" type="button" aria-label={t("Aumentar zoom")}
        aria-controls={controls} aria-disabled={zoom >= 4} onClick={() => { if (zoom < 4) onStep(1); }}>+</button>
    </div>
  );
}
