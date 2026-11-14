import Observatory from "../../components/observatorio/observatory";
import { metadataFor, routes } from "../../content/routes";
import { getExamples } from "../../lib/examples";
import "../../components/observatorio/observatory.css";

export const metadata = metadataFor(routes.observatorio);

export default function Page() {
  const targets = getExamples().filter((example) => !example.synthetic).map(({ slug, name, sequence }) => ({
    slug, name, ra: sequence.ra_deg, dec: sequence.dec_deg, time: sequence.frames[0].observed_at_utc,
  }));
  return (
    <main className="orbital" id="conteudo">
      <header className="shell orbital-title">
        <h1>{routes.observatorio.title}</h1>
        <p>{routes.observatorio.description}</p>
      </header>
      <Observatory targets={targets} />
    </main>
  );
}
