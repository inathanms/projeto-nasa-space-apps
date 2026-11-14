import { Sequence, SequenceError } from "@/types/sequence";

// URL da API (Render). Vazia = só exemplos estáticos.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

const TIMEOUT_MS = 60_000; // o Render Free pode levar ~1 min para acordar

/** Resolve image_src relativo ao diretório do manifest. */
function resolverImagens(seq: Sequence, base: string): Sequence {
  return {
    ...seq,
    frames: seq.frames.map((f) => ({
      ...f,
      image_src: /^(data:|https?:|\/)/.test(f.image_src) ? f.image_src : `${base}${f.image_src}`,
    })),
  };
}

function ordenar(seq: Sequence): Sequence {
  return {
    ...seq,
    frames: [...seq.frames].sort(
      (a, b) => Date.parse(a.observed_at_utc) - Date.parse(b.observed_at_utc),
    ),
  };
}

/** Exemplo pré-processado: public/examples/<slug>/manifest.json */
export async function carregarExemplo(slug: string, signal?: AbortSignal): Promise<Sequence> {
  const base = `/examples/${slug}/`;
  let res: Response;
  try {
    res = await fetch(`${base}manifest.json`, { signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new SequenceError("rede");
  }
  if (!res.ok) throw new SequenceError("exemplo_ausente");
  try {
    return ordenar(resolverImagens((await res.json()) as Sequence, base));
  } catch {
    throw new SequenceError("exemplo_ausente");
  }
}

/** Busca ao vivo na API (GET /api/v1/sequence). */
export async function buscarSequencia(ra: number, dec: number, signal?: AbortSignal): Promise<Sequence> {
  if (!API_BASE) throw new SequenceError("sem_api");

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  signal?.addEventListener("abort", () => ctrl.abort());

  const url = `${API_BASE}/api/v1/sequence?ra_deg=${encodeURIComponent(ra)}&dec_deg=${encodeURIComponent(dec)}`;
  let res: Response;
  try {
    res = await fetch(url, { signal: ctrl.signal });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new SequenceError(ctrl.signal.aborted ? "indisponivel" : "rede");
  } finally {
    clearTimeout(timer);
  }

  let corpo: unknown = null;
  try {
    corpo = await res.json();
  } catch {
    if (res.ok) throw new SequenceError("rede", "Resposta não JSON");
  }

  if (res.ok) return ordenar(corpo as Sequence);
  if (res.status === 422) {
    const txt = JSON.stringify(corpo ?? "");
    throw new SequenceError("coordenada_invalida", undefined, txt.includes("dec_deg") ? "dec_deg" : "ra_deg");
  }
  if (res.status === 404) throw new SequenceError("sem_cobertura");
  if (res.status === 503 || res.status === 504) throw new SequenceError("indisponivel");
  throw new SequenceError("rede", `HTTP ${res.status}`);
}
