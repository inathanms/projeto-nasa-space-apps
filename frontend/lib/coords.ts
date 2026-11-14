// Utilidades de coordenadas (graus ICRS).

export const wrapRa = (ra: number) => ((ra % 360) + 360) % 360;
export const clampDec = (dec: number) => Math.max(-90, Math.min(90, dec));

/** Diferença angular em RA no intervalo (-180, 180]. */
export const deltaRa = (a: number, b: number) => {
  const d = wrapRa(a - b);
  return d > 180 ? d - 360 : d;
};

const nf = (casas: number) =>
  new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const fmtGraus = (v: number, casas = 2) => `${nf(casas).format(v)}°`;

export const fmtDec = (dec: number, casas = 2) =>
  `${dec >= 0 ? "+" : "−"}${nf(casas).format(Math.abs(dec))}°`;

/** RA em horas e minutos, ex.: "17h 57m". */
export const fmtRaHm = (ra: number) => {
  const totalMin = Math.round((wrapRa(ra) / 15) * 60) % (24 * 60);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${h}h ${String(m).padStart(2, "0")}m`;
};

export type ValidacaoCoord = { ok: true; ra: number; dec: number } | { ok: false; field: "ra_deg" | "dec_deg" };

/** Mesma regra da API: 0 ≤ RA < 360 e −90 ≤ Dec ≤ 90, valores finitos. Aceita vírgula decimal. */
export function validarCoordenadas(raTxt: string, decTxt: string): ValidacaoCoord {
  const ra = Number(raTxt.trim().replace(",", ".").replace("−", "-"));
  const dec = Number(decTxt.trim().replace(",", ".").replace("−", "-"));
  if (raTxt.trim() === "" || !Number.isFinite(ra) || ra < 0 || ra >= 360) return { ok: false, field: "ra_deg" };
  if (decTxt.trim() === "" || !Number.isFinite(dec) || dec < -90 || dec > 90) return { ok: false, field: "dec_deg" };
  return { ok: true, ra, dec };
}

const mesCurto = new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric", timeZone: "UTC" });
const completo = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

/** "mai/2025" */
export const fmtEpoca = (iso: string) => {
  const partes = mesCurto.formatToParts(new Date(iso));
  const mes = (partes.find((p) => p.type === "month")?.value ?? "").replace(".", "");
  const ano = partes.find((p) => p.type === "year")?.value ?? "";
  return `${mes.charAt(0).toUpperCase()}${mes.slice(1)}/${ano}`;
};

/** "12 de mai. de 2025, 03:14 UTC" */
export const fmtDataUtc = (iso: string) => `${completo.format(new Date(iso))} UTC`;
