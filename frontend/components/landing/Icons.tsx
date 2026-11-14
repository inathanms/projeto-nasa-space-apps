import type { IconKey } from "../../content/landing";

const common = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: false,
};

const paths: Record<IconKey, React.ReactNode> = {
  // olho com metade "infravermelha"
  invisivel: (
    <>
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 8.8a3.2 3.2 0 0 1 0 6.4Z" fill="currentColor" />
    </>
  ),
  // setas de troca
  epocas: (
    <>
      <path d="M4 8h14l-3.5-3.5" />
      <path d="M20 16H6l3.5 3.5" />
    </>
  ),
  // brilho / estrela de 4 pontas
  historias: (
    <>
      <path d="M12 3c.6 4.6 2.4 6.4 7 7-4.6.6-6.4 2.4-7 7-.6-4.6-2.4-6.4-7-7 4.6-.6 6.4-2.4 7-7Z" />
      <path d="M19 3v3M17.5 4.5h3" />
    </>
  ),
  // lupa
  cidada: (
    <>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m15 15 5.5 5.5" />
      <circle cx="10.5" cy="10.5" r="1.4" fill="currentColor" />
    </>
  ),
  // satélite
  satelite: (
    <>
      <rect x="9" y="9" width="6" height="6" rx="1.2" />
      <path d="M3 10.5h6M15 13.5h6M3 10.5v3h6M15 13.5v-3h6" />
      <path d="M12 9V6M10 5h4" />
    </>
  ),
  // arquivo / banco de dados
  arquivo: (
    <>
      <ellipse cx="12" cy="5.5" rx="7" ry="2.5" />
      <path d="M5 5.5v13c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-13" />
      <path d="M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5" />
    </>
  ),
  // cacto
  cacto: (
    <>
      <path d="M10 21V5a2 2 0 0 1 4 0v16" />
      <path d="M10 13H7.5A1.5 1.5 0 0 1 6 11.5V8" />
      <path d="M14 11h2.5A1.5 1.5 0 0 0 18 9.5V7" />
      <path d="M6 21h12" />
    </>
  ),
};

export default function Icon({ name }: { name: IconKey }) {
  return <svg {...common}>{paths[name]}</svg>;
}
