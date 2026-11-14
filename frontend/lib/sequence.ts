export type Frame = {
  frame_id: string;
  observed_at_utc: string;
  collection: string;
  detector: string | number;
  wavelength_um: number;
  bandwidth_um: number;
  calibration_version: string;
  source_url: string | null;
  cutout_url: string | null;
  valid_fraction: number;
  image_src: string;
};

export type Sequence = {
  sequence_id: string;
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: 6;
  collections: string[];
  fetched_at_utc: string | null;
  generated_at_utc: string | null;
  processing_version: string;
  is_synthetic?: boolean;
  frames: [Frame, Frame];
};

export type Example = { slug: string; name: string; sequence: Sequence; synthetic: boolean };

export function sourceLink(url: string | null) {
  try {
    const parsed = new URL(url ?? "");
    return parsed.protocol === "https:" && parsed.hostname === "irsa.ipac.caltech.edu" ? parsed.href : undefined;
  } catch {
    return undefined;
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

const validDate = (value: unknown): value is string => typeof value === "string" && Number.isFinite(Date.parse(value));
const optionalDate = (value: unknown) => value === null || validDate(value);
const optionalLink = (value: unknown) => value === null || typeof value === "string";

export function isFrame(value: unknown): value is Frame {
  if (!isRecord(value)) return false;
  return typeof value.frame_id === "string" && validDate(value.observed_at_utc) &&
    typeof value.collection === "string" && (typeof value.detector === "string" || Number.isFinite(value.detector)) &&
    Number.isFinite(value.wavelength_um) && Number.isFinite(value.bandwidth_um) &&
    typeof value.calibration_version === "string" && optionalLink(value.source_url) && optionalLink(value.cutout_url) &&
    typeof value.valid_fraction === "number" && value.valid_fraction >= 0 && value.valid_fraction <= 1 &&
    typeof value.image_src === "string" && (
      /^\/examples\/[\w-]+\/[\w-]+\.(png|svg)$/.test(value.image_src) ||
      /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(value.image_src)
    );
}

export function isSequence(value: unknown): value is Sequence {
  if (!isRecord(value)) return false;
  const { frames } = value;
  return typeof value.sequence_id === "string" && Number.isFinite(value.ra_deg) &&
    Number.isFinite(value.dec_deg) && value.fov_arcmin === 6 &&
    Array.isArray(value.collections) && value.collections.every((item: unknown) => typeof item === "string") &&
    optionalDate(value.fetched_at_utc) && optionalDate(value.generated_at_utc) &&
    typeof value.processing_version === "string" &&
    (value.is_synthetic === undefined || typeof value.is_synthetic === "boolean") &&
    Array.isArray(frames) && frames.length === 2 && isFrame(frames[0]) && isFrame(frames[1]) &&
    Date.parse(frames[0].observed_at_utc) < Date.parse(frames[1].observed_at_utc);
}

const utc = new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeZone: "UTC" });
export function formatDate(date: string) {
  return utc.format(new Date(date));
}
