import Link from "next/link";
import { marca, nav } from "@/content/landing";
import CtaLabel from "./CtaLabel";
import s from "./landing.module.css";

export default function Nav() {
  return (
    <header className={s.nav}>
      <div className={s.navInner}>
        <Link href="/" className={s.brand}>
          <img src={marca.logoMark} alt={marca.logoAlt} width={46} height={46} />
          <span>
            {marca.nome}
            <span className={s.brandTech}>{marca.nomeDestaque}</span>
            <small className={s.brandSub}>{marca.subtitulo}</small>
          </span>
        </Link>
        <nav aria-label={nav.rotuloMenu}>
          <ul className={s.navLinks}>
            {nav.links.map((l) => (
              <li key={l.href}>
                <a href={l.href}>{l.label}</a>
              </li>
            ))}
          </ul>
        </nav>
        <Link href={nav.cta.href} className={s.navDesafio}>
          <CtaLabel label={nav.cta.label} estrela={false} />
        </Link>
      </div>
    </header>
  );
}
