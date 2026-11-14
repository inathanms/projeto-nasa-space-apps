import Image from "next/image";
import Link from "next/link";
import { alvos, alvosSecao } from "../../content/landing";
import styles from "./landing.module.css";

export default function Alvos() {
  return (
    <section id="alvos" className={styles.section} aria-labelledby="alvos-titulo">
      <div className="wrap">
        <p className={styles.kicker}>{alvosSecao.kicker}</p>
        <h2 id="alvos-titulo" className={styles.h2}>{alvosSecao.titulo}</h2>
        <p className={styles.lead}>{alvosSecao.lead}</p>
        <ul className={styles.targets}>
          {alvos.map(({ slug, nome, texto, tag }) => (
            <li key={slug}>
              <Link href={alvosSecao.hrefBase + slug} className={styles.target}>
                <div className={styles.targetImage}>
                  <Image src={`/alvos/${slug}.jpg`} alt={alvosSecao.fotoAlt(nome)} width={600} height={425} loading="eager" fetchPriority="low" />
                </div>
                <div className={styles.targetBody}>
                  <h3>{nome}</h3>
                  <p>{texto}</p>
                  <div className={styles.targetFoot}>
                    <span data-kind={tag} className={styles.pill}>{alvosSecao.rotuloTag[tag]}</span>
                    <span aria-hidden="true">→</span>
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
