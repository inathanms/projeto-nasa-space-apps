import { getLanding } from "../../content/landing";
import { type Locale } from "../../lib/i18n";
import s from "./landing.module.css";

export default function ComoFunciona({ locale }: { locale: Locale }) {
  const { comoFunciona } = getLanding(locale);
  return (
    <section id="como-funciona" className={`${s.section} ${s.cream}`} aria-labelledby="como-titulo" tabIndex={-1}>
      <div className="wrap">
        <p className={s.kicker}>{comoFunciona.kicker}</p>
        <h2 id="como-titulo" className={s.h2}>{comoFunciona.titulo}</h2>
        <p className={s.lead}>{comoFunciona.lead}</p>
        <ol className={s.steps} role="list">
          {comoFunciona.passos.map((p, i) => (
            <li key={p.titulo} className={`${s.card} ${s.step}`}>
              <span className={s.num} aria-hidden="true">{i + 1}</span>
              <div>
                <h3>{p.titulo}</h3>
                <p>{p.texto}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
