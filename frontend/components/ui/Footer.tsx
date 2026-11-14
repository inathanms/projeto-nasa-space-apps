import Link from "next/link";
import { alvosSecao, dados, footer, nav } from "../../content/landing";

export default function Footer() {
  return (
    <footer className="site-footer" id="rodape">
      <div className="shell site-footer-inner">
        <p>{footer.esquerda}</p>
        <nav aria-label="Ferramentas">
          {nav.ferramentas.map(({ href, label }) => <Link href={href} key={href}>{label}</Link>)}
        </nav>
        <p>{footer.direita}</p>
        <p>{dados.credito}</p>
        <p className="landing-links">{alvosSecao.credito}</p>
      </div>
    </footer>
  );
}
