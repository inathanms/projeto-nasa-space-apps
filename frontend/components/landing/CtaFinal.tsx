import Link from "next/link";
import { ctaFinal } from "../../content/landing";
import styles from "./landing.module.css";

export default function CtaFinal() {
  return (
    <section id="cta-final" className={styles.ctaWrap} aria-labelledby="cta-titulo">
      <div className={`wrap ${styles.ctaBand}`}>
        <div>
          <h2 id="cta-titulo" className={styles.h2}>{ctaFinal.titulo}</h2>
          <p>{ctaFinal.texto}</p>
        </div>
        <div className={styles.ctaActions}>
          {ctaFinal.acoes.map(({ href, label }, index) => (
            <Link className={`button ${index === 0 ? styles.creamButton : styles.ghostButton}`} href={href} key={href}>
              {label} <span aria-hidden="true">→</span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
