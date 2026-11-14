"use client";

import { useEffect, useRef } from "react";

// Globo terrestre a partir de imagem de satélite real (NASA Blue Marble, domínio público),
// guardada em public/terra/. Projeção ortográfica (como uma foto do espaço) num <canvas>.
// A geometria da esfera é pré-calculada uma vez; a cada quadro só a longitude desloca,
// então girar a Terra é barato (só leitura de pixels).

export const TEXTURA_TERRA = "/terra/terra-blue-marble-2048.jpg";

type Props = {
  /** centro e raio da Terra, em unidades do viewBox do Palco */
  cx: number;
  cy: number;
  r: number;
  /** janela (em unidades do viewBox) que o canvas cobre — só a parte visível do disco */
  x0: number;
  y0: number;
  largura: number;
  altura: number;
  /** longitude central em graus (gira com a RA) */
  longitude: number;
  /** pixels de canvas por unidade do viewBox */
  densidade?: number;
};

type Mapa = {
  w: number;
  h: number;
  pixels: Uint32Array; // textura RGBA empacotada
  idx: Int32Array; // por pixel do canvas: linha da textura * w (ou −1 fora do disco)
  lon: Float32Array; // longitude-base (em pixels da textura) de cada pixel
  luz: Uint8Array; // sombreamento 0..255
};

export default function TerraGlobo({ cx, cy, r, x0, y0, largura, altura, longitude, densidade = 2 }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const mapa = useRef<Mapa | null>(null);
  const lonRef = useRef(longitude);
  lonRef.current = longitude;

  const W = Math.round(largura * densidade);
  const H = Math.round(altura * densidade);

  // desenha com a longitude atual
  const desenhar = () => {
    const c = canvas.current;
    const m = mapa.current;
    if (!c || !m) return;
    const g = c.getContext("2d");
    if (!g) return;
    const saida = g.createImageData(W, H);
    const out = new Uint32Array(saida.data.buffer);
    const desloc = ((((lonRef.current / 360) * m.w) % m.w) + m.w) % m.w;
    const { idx, lon, luz, pixels, w } = m;
    for (let i = 0; i < idx.length; i++) {
      const linha = idx[i];
      if (linha < 0) continue;
      let tx = (lon[i] + desloc) | 0;
      if (tx >= w) tx -= w;
      const p = pixels[linha + tx];
      const k = luz[i];
      // little-endian: 0xAABBGGRR
      const rr = ((p & 0xff) * k) >> 8;
      const gg = (((p >> 8) & 0xff) * k) >> 8;
      const bb = (((p >> 16) & 0xff) * k) >> 8;
      out[i] = 0xff000000 | (bb << 16) | (gg << 8) | rr;
    }
    g.putImageData(saida, 0, 0);
  };

  // carrega a textura e pré-calcula a esfera
  useEffect(() => {
    let vivo = true;
    const img = new Image();
    img.src = TEXTURA_TERRA;
    img.decode().then(() => {
      if (!vivo) return;
      const tw = img.naturalWidth;
      const th = img.naturalHeight;
      const tc = document.createElement("canvas");
      tc.width = tw;
      tc.height = th;
      const tg = tc.getContext("2d", { willReadFrequently: true });
      if (!tg) return;
      tg.drawImage(img, 0, 0);
      const pixels = new Uint32Array(tg.getImageData(0, 0, tw, th).data.buffer);

      const n = W * H;
      const idx = new Int32Array(n).fill(-1);
      const lon = new Float32Array(n);
      const luz = new Uint8Array(n);
      // luz vindo do alto à direita, um pouco de frente
      const L = [0.62, -0.38, 0.69];
      const LN = Math.hypot(L[0], L[1], L[2]);
      for (let py = 0; py < H; py++) {
        const vy = (y0 + (py + 0.5) / densidade - cy) / r;
        for (let px = 0; px < W; px++) {
          const vx = (x0 + (px + 0.5) / densidade - cx) / r;
          const d2 = vx * vx + vy * vy;
          if (d2 >= 1) continue;
          const z = Math.sqrt(1 - d2);
          const lat = Math.asin(-vy); // y da tela cresce para baixo
          const lo = Math.atan2(vx, z); // −π..π
          const ty = Math.min(th - 1, Math.max(0, ((0.5 - lat / Math.PI) * th) | 0));
          const i = py * W + px;
          idx[i] = ty * tw;
          lon[i] = (lo / (2 * Math.PI) + 0.5) * tw;
          const difusa = Math.max(0, (vx * L[0] + vy * L[1] + z * L[2]) / LN);
          const borda = Math.pow(z, 0.35); // escurece de leve perto do limbo
          luz[i] = Math.min(255, Math.round(255 * (0.1 + 0.95 * difusa) * borda));
        }
      }
      mapa.current = { w: tw, h: th, pixels, idx, lon, luz };
      desenhar();
    });
    return () => {
      vivo = false;
    };
    // a geometria só muda se a janela mudar
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [W, H, cx, cy, r, x0, y0, densidade]);

  // redesenha quando a longitude muda (1 quadro por vez)
  const pedido = useRef(0);
  useEffect(() => {
    cancelAnimationFrame(pedido.current);
    pedido.current = requestAnimationFrame(desenhar);
    return () => cancelAnimationFrame(pedido.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [longitude]);

  return (
    <foreignObject x={x0} y={y0} width={largura} height={altura} style={{ pointerEvents: "none" }}>
      <canvas ref={canvas} width={W} height={H} style={{ width: "100%", height: "100%", display: "block" }} />
    </foreignObject>
  );
}
