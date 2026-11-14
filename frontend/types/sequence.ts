// Contrato da sequência (PLANO-MVP §3). O mesmo formato serve para
// a resposta da API (GET /api/v1/sequence) e para os exemplos estáticos
// em public/examples/<alvo>/manifest.json.

export type Frame = {
  frame_id: string;
  observed_at_utc: string; // ISO 8601, UTC
  collection: string; // ex.: "spherex_dr1" | "spherex_qr3"
  detector: number | string;
  wavelength_um: number;
  bandwidth_um: number;
  calibration_version: string;
  source_url: string | null;
  cutout_url: string | null;
  valid_fraction: number; // 0..1
  image_src: string; // data URL (API) ou caminho do PNG (exemplo)
  /** Opcional (só exemplos): posição do alvo no quadro, em fração 0..1 (x→direita, y→baixo). */
  marker?: { x: number; y: number };
};

export type Sequence = {
  sequence_id: string;
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: number;
  collections: string[];
  fetched_at_utc: string;
  generated_at_utc: string;
  processing_version: string;
  frames: Frame[];
  /** Opcional: true quando os quadros são de teste (não vieram do IRSA). */
  is_synthetic?: boolean;
};

export type SequenceErrorKind =
  | "coordenada_invalida" // 422
  | "sem_cobertura" // 404 insufficient_coverage
  | "indisponivel" // 503 / 504
  | "rede" // falha de rede / resposta não JSON
  | "sem_api" // NEXT_PUBLIC_API_BASE_URL não configurada
  | "exemplo_ausente"; // manifest do exemplo não encontrado

export class SequenceError extends Error {
  constructor(
    public kind: SequenceErrorKind,
    message?: string,
    public field?: "ra_deg" | "dec_deg",
  ) {
    super(message ?? kind);
  }
}
