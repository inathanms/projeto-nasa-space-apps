import Observatory from "../../components/observatorio/observatory";
import { getRoutes } from "../../content/routes";
import { type Locale } from "../../lib/i18n";
import { getExamples } from "../../lib/examples";
import "../../components/observatorio/observatory.css";

export default function Page({ locale }: { locale: Locale }) {
  const routes = getRoutes(locale);
  const targets = getExamples(locale, { includePresets: true }).filter((example) => example.preset).map(({ slug, name, sequence }) => ({
    slug, name, ra: sequence.ra_deg, dec: sequence.dec_deg, time: sequence.frames[0].observed_at_utc,
  }));
  return (
    <main className="orbital" id="conteudo" tabIndex={-1}>
      <header className="shell orbital-title">
        <h1>{routes.observatorio.title}</h1>
        <p>{routes.observatorio.description}</p>
      </header>
      <Observatory targets={targets} />
    </main>
  );
}
