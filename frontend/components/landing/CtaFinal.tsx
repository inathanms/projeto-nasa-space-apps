import Link from "next/link";
import { getLanding } from "../../content/landing";
import { localizedHref, type Locale } from "../../lib/i18n";
import styles from "./landing.module.css";

export default function CtaFinal({ locale }: { locale: Locale }) {
  const { ctaFinal } = getLanding(locale);
  return (
    <section id="cta-final" className={styles.ctaWrap} aria-labelledby="cta-titulo">
      <div className={`wrap ${styles.ctaBand}`}>
        <div>
          <h2 id="cta-titulo" className={styles.h2}>{ctaFinal.titulo}</h2>
          <p>{ctaFinal.texto}</p>
        </div>
        <div className={styles.ctaActions}>
          {ctaFinal.acoes.map(({ href, label }, index) => (
            <Link className={`button ${index === 0 ? styles.creamButton : styles.ghostButton}`} href={localizedHref(locale, href)} key={href}>
              {label} <span aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
