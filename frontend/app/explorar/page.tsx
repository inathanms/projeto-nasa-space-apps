import Explorer from "../../components/explorar/explorer";
import { metadataFor, routes } from "../../content/routes";
import { getExamples } from "../../lib/examples";
import "../../components/explorar/explorer.css";

export const metadata = metadataFor(routes.explorar);

export default function Page() {
  return (
    <main id="conteudo" className="shell explorer" tabIndex={-1}>
      <header className="explorer-head">
        <h1>{routes.explorar.title}</h1>
        <p>{routes.explorar.description}</p>
      </header>
      <Explorer examples={getExamples()} />
    </main>
  );
}
