import Link from "next/link";
import { localizedHref, translators, type Locale } from "../../lib/i18n";

export default function Missing({ locale }: { locale: Locale }) {
  const t = translators[locale];
  return (
    <main id="conteudo" className="shell not-found" tabIndex={-1}>
      <h1>{t("Página não encontrada")}</h1>
      <p>{t("Confira o endereço ou volte à página inicial.")}</p>
      <Link className="button primary" href={localizedHref(locale, "/")}>{t("Voltar ao início")}</Link>
    </main>
  );
}
