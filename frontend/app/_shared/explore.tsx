import Explorer from "../../components/explorar/explorer";
import { getRoutes } from "../../content/routes";
import { type Locale } from "../../lib/i18n";
import { getExamples } from "../../lib/examples";
import "../../components/explorar/explorer.css";

const proxy = "/api/spherex-dev";
const configuredApi = process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/+$/, "");
const apiBase = process.env.VERCEL_GIT_COMMIT_REF === "develop"
  ? proxy
  : configuredApi || (process.env.NODE_ENV === "development" ? proxy : undefined);

export default function Page({ locale }: { locale: Locale }) {
  const routes = getRoutes(locale);
  return (
    <main id="conteudo" className="shell explorer" tabIndex={-1}>
      <header className="explorer-head">
        <h1>{routes.explorar.title}</h1>
        <p>{routes.explorar.description}</p>
      </header>
      <Explorer examples={getExamples(locale, { includePresets: true })} api={apiBase} />
    </main>
  );
}
