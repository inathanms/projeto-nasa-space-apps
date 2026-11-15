import Image from "next/image";
import Link from "next/link";
import { marca, nav } from "../../content/landing";
import Menu from "./Menu";

export default function Nav() {
  return (
    <header className="site-header">
      <div className="shell site-header-inner">
        <Link className="site-brand" href="/">
          <Image src={marca.logoIcon} alt="" width={44} height={44} loading="eager" />
          <span>
            <strong>{marca.nome}<span>{marca.nomeDestaque}</span></strong>
            <small>{marca.subtitulo}</small>
          </span>
        </Link>
        <nav className="site-links landing-links" aria-label="Nesta página">
          {nav.links.map(({ href, label }) => <Link href={href} key={href}>{label}</Link>)}
        </nav>
        <nav className="site-links tool-links" aria-label={nav.rotuloMenu}>
          {nav.ferramentas.map(({ href, label }) => <Link href={href} key={href}>{label}</Link>)}
        </nav>
        <Link className="button primary header-cta" href={nav.cta.href}>
          {nav.cta.label} <span aria-hidden="true">→</span>
        </Link>
        <Menu label={nav.menu}>
          <nav aria-label={nav.rotuloMenu}>
            {nav.ferramentas.map(({ href, label }) => <Link href={href} key={href}>{label}</Link>)}
            {nav.links.map(({ href, label }) => <Link href={href} key={href} className="landing-links">{label}</Link>)}
          </nav>
        </Menu>
      </div>
    </header>
  );
}
