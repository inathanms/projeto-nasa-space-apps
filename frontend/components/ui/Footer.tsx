import { getLanding } from "../../content/landing";
import { translators, type Locale } from "../../lib/i18n";
import ToolLinks from "./ToolLinks";

export default function Footer({ locale }: { locale: Locale }) {
  const { alvosSecao, dados, footer, nav } = getLanding(locale);
  const t = translators[locale];
  return (
    <footer className="site-footer" id="rodape">
      <div className="shell site-footer-inner">
        <p>{footer.esquerda}</p>
        <nav aria-label={t("Ferramentas no rodapé")}>
          <ToolLinks links={nav.ferramentas} />
        </nav>
        <p>{footer.direita}</p>
        <p>{dados.credito}</p>
        <p className="landing-links">{alvosSecao.credito}</p>
      </div>
    </footer>
  );
}
