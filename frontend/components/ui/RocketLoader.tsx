/**
 * Indicador de carregamento: um foguetinho dando voltas ao redor de um planeta.
 * Não tem role própria: quem usa decide se fica dentro de uma região role="status".
 * `inline` é a versão compacta (texto ao lado), para linhas de status; a padrão é maior, para visores e cenas.
 */
export default function RocketLoader({ label, inline = false }: { label: string; inline?: boolean }) {
  return (
    <span className="rocket-loader" data-inline={inline}>
      <span className="rocket-loader-sky" aria-hidden="true">
        <span className="rocket-loader-ring" />
        <span className="rocket-loader-planet" />
        <span className="rocket-loader-orbit">
          <svg className="rocket-loader-rocket" viewBox="0 0 48 48">
            <path className="rocket-loader-flame" d="M19 34c1 5 3 8 5 10 2-2 4-5 5-10z" />
            <path className="rocket-loader-fin" d="M17 26l-6 7 1 3 6-3zM31 26l6 7-1 3-6-3z" />
            <path className="rocket-loader-body" d="M24 3c-6 6-8 14-8 22l2 9h12l2-9c0-8-2-16-8-22z" />
            <circle className="rocket-loader-window" cx="24" cy="18" r="3.6" />
          </svg>
        </span>
      </span>
      <span className="rocket-loader-label">{label}</span>
    </span>
  );
}
