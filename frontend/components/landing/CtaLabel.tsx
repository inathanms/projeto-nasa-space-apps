import s from "./landing.module.css";

// Conteúdo padrão dos botões "Explorar o céu": brilho + texto + seta que avança no hover.
export default function CtaLabel({ label, estrela = true }: { label: string; estrela?: boolean }) {
  return (
    <>
      {estrela && (
        <svg className={s.ctaStar} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path
            d="M12 2c.7 5.4 2.6 7.3 8 8-5.4.7-7.3 2.6-8 8-.7-5.4-2.6-7.3-8-8 5.4-.7 7.3-2.6 8-8Z"
            fill="currentColor"
          />
        </svg>
      )}
      <span>{label}</span>
      <span className={s.ctaArrow} aria-hidden="true">→</span>
    </>
  );
}
