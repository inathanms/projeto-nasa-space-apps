import Link from "next/link";
import PointingLab from "../../components/laboratorio/pointing-lab";
import { metadataFor, routes } from "../../content/routes";
import { getExamples } from "../../lib/examples";
import "../../components/laboratorio/pointing-lab.css";

export const metadata = metadataFor(routes.laboratorio);

export default function Page() {
  const targets = getExamples().filter((example) => !example.synthetic).map(({ name, sequence }) => ({
    name, ra: sequence.ra_deg, dec: sequence.dec_deg,
  }));

  return (
    <main id="conteudo" className="shell pointing-lab" tabIndex={-1}>
      <header className="pointing-heading">
        <h1>{routes.laboratorio.title}</h1>
        <p>{routes.laboratorio.description}</p>
        <Link className="button secondary" href="/observatorio/">Abrir o observatório orbital</Link>
      </header>
      <PointingLab targets={targets} />
    </main>
  );
}
