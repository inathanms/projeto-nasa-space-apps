import Image from "next/image";
import { getLanding } from "../../content/landing";
import { type Locale } from "../../lib/i18n";
import s from "./landing.module.css";

export default function Sobre({ locale }: { locale: Locale }) {
  const { marca, sobre } = getLanding(locale);
  return (
    <section id="sobre" className={`${s.section} ${s.cream}`} aria-labelledby="sobre-titulo" tabIndex={-1}>
      <div className={`wrap ${s.about}`}>
        <Image className={s.aboutLogo} src={marca.logoMark} alt={marca.logoAlt} width={300} height={300} />
        <div>
          <p className={s.kicker}>{sobre.kicker}</p>
          <h2 id="sobre-titulo" className={s.h2}>{sobre.titulo}</h2>
          {sobre.paragrafos.map((p) => (
            <p key={p} className={s.lead}>{p}</p>
          ))}
        </div>
      </div>
    </section>
  );
}
