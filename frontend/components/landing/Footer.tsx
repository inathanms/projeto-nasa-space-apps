import { footer } from "@/content/landing";
import s from "./landing.module.css";

export default function Footer() {
  return (
    <footer className={s.footer}>
      <div className={s.footerInner}>
        <span>{footer.esquerda}</span>
        <span>{footer.direita}</span>
      </div>
    </footer>
  );
}
