import { alvosSecao, dados, footer } from "../../content/landing";
import ToolLinks from "./ToolLinks";

export default function Footer() {
  return (
    <footer className="site-footer" id="rodape">
      <div className="shell site-footer-inner">
        <p>{footer.esquerda}</p>
        <nav aria-label="Ferramentas no rodapé">
          <ToolLinks />
        </nav>
        <p>{footer.direita}</p>
        <p>{dados.credito}</p>
        <p className="landing-links">{alvosSecao.credito}</p>
      </div>
    </footer>
  );
}
