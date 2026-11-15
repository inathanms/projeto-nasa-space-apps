import { forLocales, type Locale } from "./i18n";

export type Frame = {
  frame_id: string;
  observed_at_utc: string;
  collection: string;
  detector: string | number;
  wavelength_um: number;
  bandwidth_um: number;
  wavelength_bands_um?: [number, number][];
  calibration_version: string;
  source_url: string | null;
  cutout_url: string | null;
  valid_fraction: number | null;
  image_src: string;
};

type Frames = [Frame, ...Frame[]];

export type Sequence = {
  sequence_id: string;
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: number;
  collections: string[];
  fetched_at_utc: string | null;
  generated_at_utc: string | null;
  processing_version: string;
  is_synthetic?: boolean;
  frames: Frames;
  rgb_frames?: Frames;
};

export type Example = { slug: string; name: string; sequence: Sequence; synthetic: boolean; preset: boolean };

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
    (value.wavelength_bands_um === undefined || (Array.isArray(value.wavelength_bands_um) &&
      value.wavelength_bands_um.length > 0 && value.wavelength_bands_um.every((band: unknown) =>
        Array.isArray(band) && band.length === 2 && Number.isFinite(band[0]) && Number.isFinite(band[1]) && band[0] < band[1]))) &&
    typeof value.calibration_version === "string" && optionalLink(value.source_url) && optionalLink(value.cutout_url) &&
    (value.valid_fraction === null || (typeof value.valid_fraction === "number" &&
      value.valid_fraction >= 0 && value.valid_fraction <= 1)) &&
    typeof value.image_src === "string" && (
      /^\/examples\/[\w-]+\/[\w-]+\.(png|svg)$/.test(value.image_src) ||
      /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(value.image_src)
    );
}

function isFrames(value: unknown): value is Frames {
  return Array.isArray(value) && value.length > 0 && value.every(isFrame) &&
    value.every((frame, index) => index === 0 ||
      Date.parse(value[index - 1].observed_at_utc) < Date.parse(frame.observed_at_utc));
}

export function isSequence(value: unknown): value is Sequence {
  if (!isRecord(value)) return false;
  return typeof value.sequence_id === "string" && Number.isFinite(value.ra_deg) &&
    Number.isFinite(value.dec_deg) && typeof value.fov_arcmin === "number" &&
    Number.isFinite(value.fov_arcmin) && value.fov_arcmin > 0 &&
    Array.isArray(value.collections) && value.collections.every((item: unknown) => typeof item === "string") &&
    optionalDate(value.fetched_at_utc) && optionalDate(value.generated_at_utc) &&
    typeof value.processing_version === "string" &&
    (value.is_synthetic === undefined || typeof value.is_synthetic === "boolean") &&
    isFrames(value.frames) && (value.rgb_frames === undefined || isFrames(value.rgb_frames));
}

const utc = forLocales((language) => new Intl.DateTimeFormat(language, { dateStyle: "medium", timeZone: "UTC" }));
export function formatDate(date: string, locale: Locale = "en") {
  return utc[locale].format(new Date(date));
}
