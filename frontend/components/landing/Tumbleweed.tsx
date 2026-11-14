import s from "./landing.module.css";

// "Bola de mato" de faroeste que atravessa as dunas a cada 10s.
// Só CSS (sem JS): ciclo definido em landing.module.css (.tumble*).
// Desligada com prefers-reduced-motion.

// Galhos gerados de forma determinística (mesmo resultado no build e no cliente).
const galhos = Array.from({ length: 14 }, (_, i) => {
  const ang = (i * 360) / 14 + (i % 3) * 9;
  const rx = 30 - (i % 4) * 4;
  const ry = 12 + (i % 5) * 3;
  return { ang, rx, ry, cor: i % 3 === 0 ? "#e2b778" : i % 3 === 1 ? "#b9864c" : "#8d5f30" };
});

export default function Tumbleweed() {
  return (
    <div className={s.tumbleLane} aria-hidden="true">
      <div className={s.tumbleShadow} />
      <div className={s.tumbleHop}>
        <div className={s.tumbleSpin}>
          <svg viewBox="-40 -40 80 80" width="100%" height="100%" focusable="false">
            <circle r={30} fill="#8d5f30" opacity={0.18} />
            <g fill="none" strokeWidth={1.6} strokeLinecap="round">
              {galhos.map((g, i) => (
                <ellipse
                  key={i}
                  rx={g.rx}
                  ry={g.ry}
                  stroke={g.cor}
                  transform={`rotate(${g.ang})`}
                />
              ))}
              <path
                d="M-26 -8 Q-10 -24 6 -14 T28 -4 M-22 14 Q-4 2 12 18 T24 10 M-8 -28 Q4 -6 -6 10 T2 28 M10 -26 Q18 -4 4 8 T-14 24"
                stroke="#c99a5e"
              />
            </g>
          </svg>
        </div>
      </div>
    </div>
  );
}
