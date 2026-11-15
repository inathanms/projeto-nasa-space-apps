import Image from "next/image";
import Link from "next/link";
import { getLanding } from "../../content/landing";
import { localizedHref, type Locale } from "../../lib/i18n";
import styles from "./landing.module.css";

export default function Alvos({ locale }: { locale: Locale }) {
  const { alvos, alvosSecao } = getLanding(locale);
  return (
    <section id="alvos" className={styles.section} aria-labelledby="alvos-titulo" tabIndex={-1}>
      <div className="wrap">
        <p className={styles.kicker}>{alvosSecao.kicker}</p>
        <h2 id="alvos-titulo" className={styles.h2}>{alvosSecao.titulo}</h2>
        <p className={styles.lead}>{alvosSecao.lead}</p>
        <ul className={styles.targets} role="list">
          {alvos.map(({ slug, nome, texto, tag }) => (
            <li key={slug} className={styles.target}>
              <div className={styles.targetImage}>
                <Image src={`/alvos/${slug}.jpg`} alt={alvosSecao.fotoAlt(nome)} width={600} height={425} />
              </div>
              <div className={styles.targetBody}>
                <h3><Link href={localizedHref(locale, alvosSecao.hrefBase + slug)} className={styles.targetLink}
                  aria-describedby={`alvo-${slug}-descricao`}>{nome}</Link></h3>
                <p id={`alvo-${slug}-descricao`}>{texto}</p>
                <div className={styles.targetFoot}>
                  <span data-kind={tag} className={styles.pill}>{alvosSecao.rotuloTag[tag]}</span>
                  <span aria-hidden="true">→</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
