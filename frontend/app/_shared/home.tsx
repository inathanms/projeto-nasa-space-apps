import type { Locale } from "../../lib/i18n";
import Alvos from "../../components/landing/Alvos";
import ComoFunciona from "../../components/landing/ComoFunciona";
import CtaFinal from "../../components/landing/CtaFinal";
import CtaFixo from "../../components/landing/CtaFixo";
import Dados from "../../components/landing/Dados";
import Hero from "../../components/landing/Hero";
import HeroMotion from "../../components/landing/HeroMotion";
import PorQue from "../../components/landing/PorQue";
import Sobre from "../../components/landing/Sobre";
export default function Home({ locale }: { locale: Locale }) {
  return (
    <main id="conteudo" tabIndex={-1}>
      <HeroMotion><Hero locale={locale} /></HeroMotion>
      <PorQue locale={locale} />
      <ComoFunciona locale={locale} />
      <Alvos locale={locale} />
      <Dados locale={locale} />
      <Sobre locale={locale} />
      <CtaFinal locale={locale} />
      <CtaFixo locale={locale} />
    </main>
  );
}
