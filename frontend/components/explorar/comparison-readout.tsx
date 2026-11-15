"use client";

import { useEffect, useState } from "react";
import { compareRegions } from "../../lib/comparison-readout";
import { formatDate, type Frame } from "../../lib/sequence";
import { readPngPixels } from "../../lib/spherex-api";

const percent = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 });

async function readFrame(source: string, signal: AbortSignal) {
  const response = await fetch(source, { signal });
  return readPngPixels(await response.blob());
}

function ReadoutTable({ frames }: { frames: [Frame, Frame] }) {
  const [result, setResult] = useState<ReturnType<typeof compareRegions> | "error" | null>(null);
  const [first, second] = frames;

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([readFrame(first.image_src, controller.signal), readFrame(second.image_src, controller.signal)])
      .then(([a, b]) => {
        if (!controller.signal.aborted) setResult(compareRegions(a, b));
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult("error");
      });
    return () => controller.abort();
  }, [first.image_src, second.image_src]);

  return (
    <>
      <p className="viewer-hint">Compare a intensidade média da imagem exibida em nove regiões. Só entram pixels válidos nos dois quadros. Os valores indicam brilho na escala da imagem, sem medir o fluxo de um astro.</p>
      <p className="viewer-hint" role="status">
        {result === "error" ? "Não foi possível ler os pixels destes quadros." :
          result ? "Leitura dos quadros disponível." : "Lendo os quadros…"}
      </p>
      {result && result !== "error" && (
        <table className="comparison-readout">
          <caption>Intensidade visual média por região</caption>
          <thead><tr>
            <th scope="col">Região</th>
            <th scope="col">{formatDate(first.observed_at_utc)}</th>
            <th scope="col">{formatDate(second.observed_at_utc)}</th>
          </tr></thead>
          <tbody>
            {result.map(({ label, values }) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                {values ? <>
                  <td>{percent.format(values[0])}</td>
                  <td>{percent.format(values[1])}</td>
                </> : <td colSpan={2}>Sem pixels em comum</td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

export default function ComparisonReadout({ frames }: { frames: [Frame, Frame] }) {
  const [open, setOpen] = useState(false);
  return (
    <details className="sources" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Comparação em texto</summary>
      {open && <ReadoutTable frames={frames} />}
    </details>
  );
}
