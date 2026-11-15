import { getLanding } from "../../content/landing";
import { type Locale } from "../../lib/i18n";
import Icon from "./Icons";
import s from "./landing.module.css";

export default function PorQue({ locale }: { locale: Locale }) {
  const { porQue } = getLanding(locale);
  return (
    <section id="por-que" className={s.section} aria-labelledby="por-que-titulo" tabIndex={-1}>
      <div className="wrap">
        <p className={s.kicker}>{porQue.kicker}</p>
        <h2 id="por-que-titulo" className={s.h2}>{porQue.titulo}</h2>
        <p className={s.lead}>{porQue.lead}</p>
        <ul className={s.features}>
          {porQue.cards.map((c) => (
            <li key={c.titulo} className={s.card}>
              <div className={s.icon}>
                <Icon name={c.icone} />
              </div>
              <h3>{c.titulo}</h3>
              <p>{c.texto}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
