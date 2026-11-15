import { useLocale } from "../ui/LocaleProvider";

export type ImageMode = "single" | "rgb";

export default function ImageFormat({ mode, rgbAvailable, busy, onChange }: {
  mode: ImageMode;
  rgbAvailable: boolean;
  busy: boolean;
  onChange: (mode: ImageMode) => void;
}) {
  const { t } = useLocale();
  return (
    <label className="preset-format">
      <span>{t("Formato da imagem")}</span>
      <select className="control-field" value={mode} disabled={busy}
        onChange={(event) => onChange(event.currentTarget.value === "rgb" ? "rgb" : "single")}>
        <option value="single">{t("Tons de cinza")}</option>
        <option value="rgb" disabled={!rgbAvailable}>{rgbAvailable ? t("Composição RGB") : t("Composição RGB indisponível")}</option>
      </select>
    </label>
  );
}
