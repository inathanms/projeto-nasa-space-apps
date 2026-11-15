import { useSyncExternalStore } from "react";

// Campo que o usuário está vendo agora (Explorador ou Observatório). O widget de descoberta
// lê daqui para preencher coordenadas e datas sem o usuário redigitar.
export type DiscoveryField = { name?: string; ra: number; dec: number; times: string[] };

let current: DiscoveryField | null = null;
const listeners = new Set<() => void>();

export function setDiscoveryField(field: DiscoveryField | null) {
  current = field;
  listeners.forEach((listener) => listener());
}

export function useDiscoveryField() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => current,
    () => null,
  );
}

const pad = (value: number, size: number, decimals = 0) => value.toFixed(decimals).padStart(size, "0");

/** Ascensão reta em horas, minutos e segundos: "HH MM SS.sss". */
export function raHMS(deg: number, decimals = 3) {
  let seconds = Number(((((deg % 360) + 360) % 360) / 15 * 3600).toFixed(decimals));
  if (seconds >= 86400) seconds -= 86400;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds - h * 3600) / 60);
  const s = seconds - h * 3600 - m * 60;
  return `${pad(h, 2)} ${pad(m, 2)} ${pad(s, decimals ? 3 + decimals : 2, decimals)}`;
}

/** Declinação em graus, minutos e segundos com sinal: "+DD MM SS.ss". */
export function decDMS(deg: number, decimals = 2) {
  const sign = deg < 0 ? "-" : "+";
  const total = Number((Math.abs(deg) * 3600).toFixed(decimals));
  const d = Math.floor(total / 3600);
  const m = Math.floor((total - d * 3600) / 60);
  const s = total - d * 3600 - m * 60;
  return `${sign}${pad(d, 2)} ${pad(m, 2)} ${pad(s, decimals ? 3 + decimals : 2, decimals)}`;
}

/** Data no formato do MPC: "YYYY MM DD.dddddd" (fração do dia em UTC). */
export function mpcDate(iso: string) {
  const date = new Date(iso);
  const fraction = (date.getUTCHours() * 3600 + date.getUTCMinutes() * 60 + date.getUTCSeconds() + date.getUTCMilliseconds() / 1000) / 86400;
  return `${date.getUTCFullYear()} ${pad(date.getUTCMonth() + 1, 2)} ${pad(date.getUTCDate() + fraction, 9, 6)}`;
}

/**
 * Uma linha de observação no formato de 80 colunas do MPC (MPC1992), para asteroides e cometas:
 * col 6–12 designação provisória do observador, 13 asterisco de descoberta, 15 "C" (CCD),
 * 16–32 data, 33–44 RA, 45–56 Dec, 66–70 magnitude, 71 banda, 78–80 código do observatório.
 */
export function mpcLine({ designation, discovery, iso, ra, dec, magnitude, band, code }: {
  designation: string; discovery: boolean; iso: string; ra: number; dec: number; magnitude?: string; band?: string; code: string;
}) {
  const line = " ".repeat(5)
    + designation.slice(0, 7).padEnd(7)
    + (discovery ? "*" : " ")
    + " C"
    + mpcDate(iso)
    + raHMS(ra, 3)
    + decDMS(dec, 2)
    + " ".repeat(9)
    + (magnitude ?? "").slice(0, 5).padEnd(5)
    + (band ?? " ").slice(0, 1).padEnd(1)
    + " ".repeat(6)
    + code.slice(0, 3).padEnd(3);
  return line;
}

export type ReportHeader = {
  code: string;
  contact: string;
  observers: string;
  measurer: string;
  telescope: string;
};

/** Relatório completo (cabeçalho + linhas), pronto para revisar e enviar em texto puro. */
export function mpcReport(header: ReportHeader, field: DiscoveryField, designation = "SPH0001") {
  const code = header.code.trim().toUpperCase() || "XXX";
  const lines = [
    `COD ${code}`,
    header.contact && `CON ${header.contact}`,
    header.observers && `OBS ${header.observers}`,
    header.measurer && `MEA ${header.measurer}`,
    header.telescope && `TEL ${header.telescope}`,
    `ACK ${designation}`,
    "NET Gaia DR3",
    ...field.times.map((iso, index) => mpcLine({ designation, discovery: index === 0, iso, ra: field.ra, dec: field.dec, code })),
    "----- end -----",
  ];
  return lines.filter(Boolean).join("\n");
}

/**
 * Consulta de objetos conhecidos ao redor da posição no SIMBAD (estrelas, galáxias, variáveis…).
 * Raio de 5′: o SIMBAD dá posições do ano 2000, e estrelas próximas andaram desde então
 * (Barnard ~4,5′, Epsilon Indi B ~2′). Com raio menor, elas ficariam de fora da busca.
 * O espelho de Harvard (CfA) é o principal porque o servidor da França (CDS) já ficou fora do ar.
 */
const SIMBAD_HOSTS = { harvard: "https://simbad.cfa.harvard.edu", cds: "https://simbad.cds.unistra.fr" } as const;
export const simbadUrl = (field: DiscoveryField, host: keyof typeof SIMBAD_HOSTS = "harvard", arcmin = 5) =>
  `${SIMBAD_HOSTS[host]}/simbad/sim-coo?Coord=${encodeURIComponent(`${field.ra} ${field.dec >= 0 ? "+" : ""}${field.dec}`)}&Radius=${arcmin}&Radius.unit=arcmin`;

export const MPCHECKER_URL = "https://minorplanetcenter.net/cgi-bin/checkmp.cgi";

/**
 * Link do MPChecker já preenchido (busca por posição). Os parâmetros espelham o formulário de
 * checkmp.cgi: data em ano/mês/dia decimal (UT), R.A. "HH MM SS.s", Decl. "±DD MM SS",
 * raio em minutos de arco, magnitude limite V e código do observatório (500 = geocêntrico).
 * As demais opções repetem os padrões do formulário.
 */
export function mpcheckerUrl(field: DiscoveryField, iso: string, radius = 5) {
  const [year, month, day] = mpcDate(iso).split(" ");
  const params = new URLSearchParams({
    year, month, day: Number(day).toFixed(5),
    which: "pos",
    ra: raHMS(field.ra, 1),
    decl: decDMS(field.dec, 0),
    TextArea: "",
    radius: String(radius),
    limit: "24.0",
    oc: "500",
    sort: "d",
    mot: "h",
    tmot: "s",
    pdes: "u",
    needed: "f",
    ps: "n",
    type: "p",
  });
  return `https://minorplanetcenter.net/cgi-bin/mpcheck.cgi?${params}`;
}
export const MPC_EMAIL = "obs@cfa.harvard.edu";
export const MPC_PSV_URL = "https://minorplanetcenter.net/submit_psv";
export const MPC_OBSCODE_URL = "https://docs.minorplanetcenter.net/mpc-ops-docs/observatory-and-program-codes/observatory-codes/";
export const VSX_URL = "https://vsx.aavso.org/index.php?view=search.top";
