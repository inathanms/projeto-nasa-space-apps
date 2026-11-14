export function parseCoordinate(raw: string) {
  const normalized = raw.trim().replace(",", ".").replace("−", "-");
  return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized) ? Number(normalized) : NaN;
}
