import Link from "next/link";
import { alvos, alvosSecao } from "@/content/landing";
import s from "./landing.module.css";

export default function Alvos() {
  return (
    <section id="alvos" className={s.section} aria-labelledby="alvos-titulo">
      <div className={s.inner}>
        <p className={s.kicker}>{alvosSecao.kicker}</p>
        <h2 id="alvos-titulo" className={s.h2}>{alvosSecao.titulo}</h2>
        <p className={s.lead}>{alvosSecao.lead}</p>
        <ul className={s.alvosGrid}>
          {alvos.map((a) => (
            <li key={a.slug}>
              <Link href={`${alvosSecao.hrefBase}${a.slug}`} className={s.alvo}>
                <div className={s.alvoImg}>
                  <img src={`/alvos/${a.slug}.jpg`} alt={alvosSecao.fotoAlt(a.nome)} width={600} height={425} loading="lazy" />
                  <span className={s.alvoMira} aria-hidden="true" />
                  <span className={s.alvoSelo}>{alvosSecao.fotoSelo}</span>
                </div>
                <div className={s.alvoBody}>
                  <h3>{a.nome}</h3>
                  <p>{a.texto}</p>
                  <p className={s.alvoNota}>{alvosSecao.fotoNota[a.slug]}</p>
                  <div className={s.alvoFoot}>
                    <span className={`${s.pill} ${a.tag === "brilho" ? s.pillBrilho : ""}`}>
                      {alvosSecao.rotuloTag[a.tag]}
                    </span>
                    <span className={s.alvoCta} aria-hidden="true">
                      {alvosSecao.cardCta} <span className={s.ctaArrow}>→</span>
                    </span>
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
        <p className={s.alvosCredito}>{alvosSecao.credito}</p>
      </div>
    </section>
  );
}
