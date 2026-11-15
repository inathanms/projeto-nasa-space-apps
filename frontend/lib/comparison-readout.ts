import { translators, type Locale } from "./i18n";

export function compareRegions(first: ImageData, second: ImageData, locale: Locale = "en") {
  const t = translators[locale];
  const rows = [t("Superior"), t("Central"), t("Inferior")];
  const columns = [t("esquerda"), t("centro"), t("direita")];
  const { width, height } = first;
  if (width !== second.width || height !== second.height) throw new Error(t("Quadros de tamanhos diferentes."));

  const regions = rows.flatMap((row) => columns.map((column) => ({
    label: `${row} · ${column}`, first: 0, second: 0, count: 0,
  })));
  for (let y = 0; y < height; y++) {
    const row = Math.floor(y * 3 / height);
    for (let x = 0; x < width; x++) {
      const pixel = (y * width + x) * 4;
      if (!first.data[pixel + 3] || !second.data[pixel + 3]) continue;
      const region = regions[row * 3 + Math.floor(x * 3 / width)];
      region.first += first.data[pixel];
      region.second += second.data[pixel];
      region.count++;
    }
  }
  return regions.map(({ label, first, second, count }) => ({
    label, values: count ? [first / (count * 255), second / (count * 255)] : null,
  }));
}
