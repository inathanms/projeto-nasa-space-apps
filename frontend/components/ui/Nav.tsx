import Image from "next/image";
import Link from "next/link";
import { getLanding } from "../../content/landing";
import { localizedHref, translators, type Locale } from "../../lib/i18n";
import LanguageSwitch from "./LanguageSwitch";
import Menu from "./Menu";
import ToolLinks from "./ToolLinks";

export default function Nav({ locale }: { locale: Locale }) {
  const { marca, nav } = getLanding(locale);
  const t = translators[locale];
  return (
    <header className="site-header">
      <div className="shell site-header-inner">
        <Link className="site-brand" href={localizedHref(locale, "/")}>
          <Image src={marca.logoIcon} alt="" width={44} height={44} loading="eager" />
          <span>
            <strong>{marca.nome}<span>{marca.nomeDestaque}</span></strong>
            <small>{marca.subtitulo}</small>
          </span>
        </Link>
        <nav className="site-links landing-links" aria-label={t("Nesta página")}>
          {nav.links.map(({ href, label }) => <Link href={localizedHref(locale, href)} key={href}>{label}</Link>)}
        </nav>
        <nav className="site-links tool-links" aria-label={nav.rotuloMenu}>
          <ToolLinks links={nav.ferramentas} />
        </nav>
        <Menu label={nav.menu}>
          <nav aria-label={nav.rotuloMenu}>
            <ToolLinks links={nav.ferramentas} />
            {nav.links.map(({ href, label }) => <Link href={localizedHref(locale, href)} key={href} className="landing-links">{label}</Link>)}
          </nav>
        </Menu>
        <LanguageSwitch />
        <Link className="button primary header-cta" href={localizedHref(locale, nav.cta.href)}>
          {nav.cta.label} <span aria-hidden="true">→</span>
        </Link>
      </div>
    </header>
  );
}
