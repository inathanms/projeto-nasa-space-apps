import Missing from "./_shared/missing";
import Site, { siteMetadata } from "./_shared/site";
import { translators } from "../lib/i18n";

export { viewport } from "./_shared/site";
export const metadata = { ...siteMetadata("en"), title: translators.en("Página não encontrada") };

export default function GlobalNotFound() {
  return <Site locale="en"><Missing locale="en" /></Site>;
}
