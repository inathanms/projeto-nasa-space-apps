import Link from "next/link";
import { releases } from "../../content/releases";
import { metadataFor, routes } from "../../content/routes";
import { getExamples } from "../../lib/examples";
import "./releases.css";

export const metadata = metadataFor(routes.entregas);

export default function Page() {
  const real = getExamples().find((example) => !example.synthetic);
  return (
    <main className="shell releases" id="conteudo">
      <h1>{routes.entregas.title}</h1>
      <p className="lede">{routes.entregas.description}</p>
      <ol className="release-log">
        {releases(real).map(({ area, title, description, action }) => (
          <li key={area}>
            <span className="instrument">{area}</span>
            <div>
              <h2>{title}</h2>
              <p>{description}</p>
              {action && <Link href={action.href}>{action.label} <span aria-hidden="true">&nbsp;↗</span></Link>}
            </div>
          </li>
        ))}
      </ol>
    </main>
  );
}
