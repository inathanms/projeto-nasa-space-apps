import { isRecord, type Frame } from "./sequence";

/** Tempo entre as imagens quando o "play" está ligado (Explorador e linha do tempo). */
export const PLAY_INTERVAL_MS = 500;

export type CatalogExposure = Pick<Frame, "frame_id" | "observed_at_utc" | "collection" |
  "source_url" | "cutout_url"> & {
  image_id: string;
  detector: string;
  observation?: {
    id: string;
    visit: number;
    minWavelength: number;
    maxWavelength: number;
  };
};

export type LiveExposure = CatalogExposure & { observation: NonNullable<CatalogExposure["observation"]> };

export type Timeline = {
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: 6;
  incomplete_collections: string[];
  truncated?: boolean;
  source?: "live";
  rgbVisits?: number[];
  exposures: CatalogExposure[];
};

export type LiveTimeline = Timeline & { truncated: boolean; exposures: LiveExposure[] };

export function rgbVisitExposures(timeline: Timeline) {
  const visits = new Set(timeline.rgbVisits);
  return timeline.exposures.filter(({ observation }) => observation && visits.delete(observation.visit));
}

export function observationIdForExposure(item: CatalogExposure) {
  if (item.observation) return item.observation.id;
  const saved = /^ivo:\/\/irsa\.ipac\/(spherex_\w+)\?([A-Za-z0-9_]{1,64})\/(D[1-6])$/.exec(item.frame_id);
  return saved && saved[1] === item.collection && saved[3] === item.detector ? saved[2] : undefined;
}

export function isTimeline(value: unknown): value is Timeline {
  return isRecord(value) && Number.isFinite(value.ra_deg) && Number.isFinite(value.dec_deg) &&
    value.fov_arcmin === 6 &&
    Array.isArray(value.incomplete_collections) &&
    value.incomplete_collections.every((item: unknown) => typeof item === "string") &&
    Array.isArray(value.exposures) && value.exposures.every((item: unknown) =>
      isRecord(item) && typeof item.image_id === "string" && /^[a-f0-9]{24}$/.test(item.image_id) &&
      typeof item.frame_id === "string" && typeof item.observed_at_utc === "string" &&
      Number.isFinite(Date.parse(item.observed_at_utc)) && typeof item.detector === "string" &&
      typeof item.collection === "string" && typeof item.source_url === "string" &&
      typeof item.cutout_url === "string");
}
