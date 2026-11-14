import Link from "next/link";
import { ctaFinal } from "@/content/landing";
import CtaLabel from "./CtaLabel";
import s from "./landing.module.css";

export default function CtaFinal() {
  return (
    <section id="cta-final" className={s.ctaWrap} aria-labelledby="cta-titulo">
      <div className={s.ctaBand}>
        <div>
          <h2 id="cta-titulo" className={s.h2}>{ctaFinal.titulo}</h2>
          <p>{ctaFinal.texto}</p>
        </div>
        <div className={s.ctaFinalAcao}>
          <Link href={ctaFinal.cta.href} className={`${s.btn} ${s.btnCream} ${s.btnHero}`}>
            <CtaLabel label={ctaFinal.cta.label} />
          </Link>
          <p className={s.ctaFinalNota}>{ctaFinal.nota}</p>
        </div>
      </div>
    </section>
  );
}
