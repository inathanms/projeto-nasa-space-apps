import Link from "next/link";
import { getLanding } from "../../content/landing";
import { localizedHref, type Locale } from "../../lib/i18n";
import HeroArt from "./HeroArt";
import { HeroMotionToggle } from "./HeroMotion";
import PlutoPlates from "./PlutoPlates";
import styles from "./landing.module.css";

export default function Hero({ locale }: { locale: Locale }) {
  const { hero, nav } = getLanding(locale);
  return (
    <section className={styles.hero} id="inicio" data-enter aria-labelledby="titulo">
      <HeroArt />
      <div className={`wrap ${styles.heroGrid}`}>
        <div className={styles.heroCopy}>
          <p className={styles.heroKicker}>{hero.kicker}</p>
          <h1 id="titulo">
            {hero.titulo.map(({ texto, destaque }) => (
              <span key={texto}>{texto}{destaque && <em>{destaque}</em>}</span>
            ))}
          </h1>
          <p className={styles.heroLead}>{hero.texto}</p>
          <div className={styles.heroActions}>
            <Link className={`button primary ${styles.heroPrimary}`} href={localizedHref(locale, nav.cta.href)}>
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2c.7 5.4 2.6 7.3 8 8-5.4.7-7.3 2.6-8 8-.7-5.4-2.6-7.3-8-8 5.4-.7 7.3-2.6 8-8Z" />
              </svg>
              {nav.cta.label}
              <svg className={styles.heroPrimaryArrow} viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 12h15m-6-6 6 6-6 6" />
              </svg>
            </Link>
            <Link className="button secondary" href={localizedHref(locale, hero.exemplo.href)}>{hero.exemplo.label}</Link>
          </div>
          <ul className={styles.heroNotes} role="list">
            {hero.selos.map((selo) => (
              <li key={selo}>
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M3 8.5 6.5 12 13 4.5" />
                </svg>
                {selo}
              </li>
            ))}
          </ul>
          <ul className={`${styles.heroNotes} ${styles.heroProof}`} role="list">
            {hero.provas.map(({ forte, texto }) => <li key={forte}><strong>{forte}</strong> {texto}</li>)}
          </ul>
          <HeroMotionToggle />
        </div>
        <PlutoPlates locale={locale} />
      </div>
    </section>
  );
}
