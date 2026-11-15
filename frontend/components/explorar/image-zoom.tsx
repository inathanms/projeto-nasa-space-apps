import { useLocale } from "../ui/LocaleProvider";

export default function ImageZoom({ zoom, onChange, controls }: {
  zoom: number;
  onChange: (zoom: number) => void;
  controls: string;
}) {
  const { t } = useLocale();
  return (
    <div className="image-zoom" role="group" aria-label={t("Zoom da imagem")}>
      <button className="button secondary" type="button" aria-label={t("Reduzir zoom")}
        aria-controls={controls} aria-disabled={zoom <= 1} onClick={() => { if (zoom > 1) onChange(zoom - 1); }}>−</button>
      <output aria-label={t("Zoom da imagem")}>{zoom}×</output>
      <button className="button secondary" type="button" aria-label={t("Aumentar zoom")}
        aria-controls={controls} aria-disabled={zoom >= 4} onClick={() => { if (zoom < 4) onChange(zoom + 1); }}>+</button>
    </div>
  );
}
