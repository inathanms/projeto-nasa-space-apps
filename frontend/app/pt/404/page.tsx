import Missing from "../../_shared/missing";
import { translators } from "../../../lib/i18n";

export const metadata = { title: translators.pt("Página não encontrada"), robots: { index: false } };

export default function Page() {
  return <Missing locale="pt" />;
}
