import { isRecord, type Frame, type Sequence } from "./sequence";
import { observationIdForExposure, type CatalogExposure, type LiveExposure, type LiveTimeline, type Timeline } from "./timeline";

const minSharedCoverage = 0.65;

type BrightnessScale = { min: string; max: string };

export type RenderedExposure = { frame: Frame; png: Blob; scale: BrightnessScale };

export class SpherexApiError extends Error {
  constructor(readonly code: string, readonly status?: number) {
    super(code);
  }
}

const isNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

async function strictFetch(url: string, signal: AbortSignal) {
  const response = await fetch(url, { signal: AbortSignal.any([signal, AbortSignal.timeout(90_000)]) });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const error = isRecord(payload) ? payload.error : undefined;
    throw new SpherexApiError(isRecord(error) && typeof error.code === "string" ? error.code : "HTTP_ERROR", response.status);
  }
  return response;
}

export function apiErrorMessage(error: unknown) {
  if (error instanceof SpherexApiError) {
    if (error.code === "NO_COMPARABLE_PAIR") return "Nenhum par de visitas do mesmo detector teve cobertura suficiente. Veja as épocas disponíveis ou abra um exemplo.";
    if (error.code === "EMPTY_IMAGE" || error.status === 404) return "Este recorte não está disponível. Tente outra exposição.";
    if (error.status === 503) return "O serviço está ocupado. Tente novamente em instantes.";
    if (error.status === 422) return "O serviço não aceitou os parâmetros enviados. Confira as coordenadas.";
    if (error.status === 504) return "O arquivo IRSA demorou mais do que o esperado. Tente novamente.";
    if (error.code === "INVALID_RESPONSE") return "O serviço devolveu dados em um formato inesperado.";
    if (error.code === "MISSING_IMAGE_METADATA") return "O serviço não disponibilizou a escala de brilho ou os metadados do recorte. Confira a configuração de CORS.";
    return "O serviço está temporariamente indisponível. Você pode abrir um exemplo.";
  }
  if (error instanceof DOMException && (error.name === "AbortError" || error.name === "TimeoutError")) {
    return "A consulta demorou mais do que o esperado. Você pode abrir um exemplo.";
  }
  return "Não foi possível conectar ao serviço. Você pode abrir um exemplo.";
}

export async function fetchEpochs(api: string, ra: number, dec: number, signal: AbortSignal): Promise<LiveTimeline> {
  const query = new URLSearchParams({ ra: String(ra), dec: String(dec) });
  const response = await strictFetch(`${api}/epochs?${query}`, signal);
  const payload: unknown = await response.json().catch(() => null);
  if (!isRecord(payload) || !isRecord(payload.query) || typeof payload.query.collection !== "string" ||
      typeof payload.truncated !== "boolean" || !Array.isArray(payload.observations)) {
    throw new SpherexApiError("INVALID_RESPONSE");
  }
  const collection = payload.query.collection;
  const exposures: LiveExposure[] = [];
  for (const value of payload.observations as unknown[]) {
    if (!isRecord(value) || typeof value.observation_id !== "string" || !/^[\w]{1,64}$/.test(value.observation_id) ||
        !isNumber(value.visit_index) || !Number.isInteger(value.visit_index) || value.visit_index < 0 ||
        typeof value.start_time !== "string" || !Number.isFinite(Date.parse(value.start_time)) ||
        !Array.isArray(value.detectors)) {
      throw new SpherexApiError("INVALID_RESPONSE");
    }
    for (const band of value.detectors as unknown[]) {
      if (!isRecord(band) || typeof band.detector !== "string" || !/^D[1-6]$/.test(band.detector) ||
          !isNumber(band.wavelength_min_um) || !isNumber(band.wavelength_max_um) ||
          band.wavelength_min_um >= band.wavelength_max_um) {
        throw new SpherexApiError("INVALID_RESPONSE");
      }
      const id = `${value.observation_id}:${band.detector}`;
      exposures.push({
        image_id: id,
        frame_id: id,
        observed_at_utc: value.start_time,
        collection,
        detector: band.detector,
        source_url: null,
        cutout_url: null,
        observation: {
          id: value.observation_id,
          visit: value.visit_index,
          minWavelength: band.wavelength_min_um,
          maxWavelength: band.wavelength_max_um,
        },
      });
    }
  }
  exposures.sort((a, b) => Date.parse(a.observed_at_utc) - Date.parse(b.observed_at_utc) ||
    a.detector.localeCompare(b.detector));
  return { ra_deg: ra, dec_deg: dec, fov_arcmin: 6, truncated: payload.truncated, incomplete_collections: [], exposures };
}

function imageDataUrl(png: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") resolve(reader.result);
      else reject(new SpherexApiError("INVALID_RESPONSE"));
    };
    reader.onerror = () => reject(new SpherexApiError("INVALID_RESPONSE"));
    reader.readAsDataURL(png);
  });
}

export async function fetchExposure(api: string, timeline: Timeline, item: CatalogExposure, signal: AbortSignal, scale?: BrightnessScale): Promise<RenderedExposure> {
  const observationId = observationIdForExposure(item);
  if (!observationId) throw new SpherexApiError("INVALID_RESPONSE");
  const params = new URLSearchParams({
    ra: String(timeline.ra_deg), dec: String(timeline.dec_deg), observation_id: observationId,
    detector: item.detector, collection: item.collection,
    size: String(timeline.fov_arcmin / 60), align: "true", colormap: "gray", upscale: "2",
  });
  if (scale) {
    params.set("scale_min", scale.min);
    params.set("scale_max", scale.max);
  }
  const response = await strictFetch(`${api}/image?${params}`, signal);
  const png = await response.blob();
  if (png.type !== "image/png" || !png.size) throw new SpherexApiError("INVALID_RESPONSE");
  const min = response.headers.get("X-Scale-Min");
  const max = response.headers.get("X-Scale-Max");
  const valid = response.headers.get("X-Valid-Pixel-Fraction");
  const validFraction = Number(valid);
  if (!min?.trim() || !max?.trim() || !valid?.trim() || !Number.isFinite(Number(min)) ||
      !Number.isFinite(Number(max)) || Number(min) >= Number(max) ||
      !Number.isFinite(validFraction) || validFraction < 0 || validFraction > 1) {
    throw new SpherexApiError("MISSING_IMAGE_METADATA");
  }
  const minWavelength = Number(response.headers.get("X-Wavelength-Min-Um") ?? item.observation?.minWavelength);
  const maxWavelength = Number(response.headers.get("X-Wavelength-Max-Um") ?? item.observation?.maxWavelength);
  if (!Number.isFinite(minWavelength) || !Number.isFinite(maxWavelength) ||
      minWavelength <= 0 || minWavelength >= maxWavelength) {
    throw new SpherexApiError("MISSING_IMAGE_METADATA");
  }
  const { observed_at_utc, collection, detector, source_url, cutout_url } = item;
  return {
    scale: { min, max },
    png,
    frame: {
      frame_id: observationId, observed_at_utc, collection, detector, source_url, cutout_url,
      wavelength_um: (minWavelength + maxWavelength) / 2,
      bandwidth_um: maxWavelength - minWavelength,
      calibration_version: "—",
      valid_fraction: validFraction,
      image_src: await imageDataUrl(png),
    },
  };
}

export function isUnavailableExposure(error: unknown) {
  return error instanceof SpherexApiError && (error.status === 404 || error.code === "EMPTY_IMAGE");
}

export async function readPngPixels(png: Blob) {
  const bitmap = await createImageBitmap(png);
  try {
    const canvas = document.createElement("canvas");
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const context = canvas.getContext("2d");
    if (!context) throw new SpherexApiError("INVALID_RESPONSE");
    context.drawImage(bitmap, 0, 0);
    return context.getImageData(0, 0, canvas.width, canvas.height);
  } finally {
    bitmap.close();
  }
}

export async function shareCoverage(first: RenderedExposure, second: RenderedExposure) {
  const a = first.frame.valid_fraction;
  const b = second.frame.valid_fraction;
  // Fractions are rounded to four places. Only decode the pixel masks if the bounds are inconclusive.
  if (a + b - 1.0001 >= minSharedCoverage) return true;
  if (Math.min(a, b) + 0.00005 < minSharedCoverage) return false;
  const [left, right] = await Promise.all([readPngPixels(first.png), readPngPixels(second.png)]);
  if (left.width !== right.width || left.height !== right.height) return false;
  let sharedPixels = 0;
  for (let index = 3; index < left.data.length; index += 4) {
    if (left.data[index] > 0 && right.data[index] > 0) sharedPixels++;
  }
  return sharedPixels / (left.width * left.height) >= minSharedCoverage;
}

function candidatePairs(exposures: LiveExposure[]) {
  const detectors = new Map<string, LiveExposure[]>();
  for (const exposure of exposures) {
    const group = detectors.get(exposure.detector);
    if (group) group.push(exposure);
    else detectors.set(exposure.detector, [exposure]);
  }
  const pairs = [];
  for (const group of detectors.values()) {
    for (const first of group.slice(0, 3)) {
      for (const second of group.slice(-3)) {
        const gap = Date.parse(second.observed_at_utc) - Date.parse(first.observed_at_utc);
        if (gap > 0 && second.observation.visit !== first.observation.visit) pairs.push({ first, second, gap });
      }
    }
  }
  return pairs.sort((a, b) => b.gap - a.gap).slice(0, 6);
}

export async function fetchComparison(api: string, timeline: LiveTimeline, signal: AbortSignal): Promise<Sequence> {
  const references = new Map<string, RenderedExposure | null>();
  for (const { first, second } of candidatePairs(timeline.exposures)) {
    signal.throwIfAborted();
    try {
      if (!references.has(first.image_id)) {
        try {
          references.set(first.image_id, await fetchExposure(api, timeline, first, signal));
        } catch (error) {
          if (!isUnavailableExposure(error)) throw error;
          references.set(first.image_id, null);
        }
      }
      const anchor = references.get(first.image_id);
      if (!anchor || anchor.frame.valid_fraction + 0.00005 < minSharedCoverage) continue;
      const other = await fetchExposure(api, timeline, second, signal, anchor.scale);
      if (!(await shareCoverage(anchor, other))) continue;
      return {
        sequence_id: `${first.image_id}/${second.image_id}`,
        ra_deg: timeline.ra_deg,
        dec_deg: timeline.dec_deg,
        fov_arcmin: timeline.fov_arcmin,
        collections: [first.collection],
        fetched_at_utc: new Date().toISOString(),
        generated_at_utc: null,
        processing_version: "SPHEREye API · norte acima · escala de brilho compartilhada",
        frames: [anchor.frame, other.frame],
      };
    } catch (error) {
      if (!isUnavailableExposure(error)) throw error;
    }
  }
  throw new SpherexApiError("NO_COMPARABLE_PAIR");
}
