import { isRecord, type Frame } from "./sequence";

export type CatalogExposure = Pick<Frame, "frame_id" | "observed_at_utc" | "collection" |
  "source_url" | "cutout_url"> & { image_id: string; detector: string };

export type Timeline = {
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: 6;
  incomplete_collections: string[];
  exposures: CatalogExposure[];
};

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
