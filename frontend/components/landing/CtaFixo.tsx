"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getLanding } from "../../content/landing";
import { localizedHref, type Locale } from "../../lib/i18n";
import styles from "./landing.module.css";

export default function CtaFixo({ locale }: { locale: Locale }) {
  const { ctaFixo } = getLanding(locale);
  const [visible, setVisible] = useState(false);
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    const hero = document.getElementById("inicio");
    const final = document.getElementById("cta-final");
    const footer = document.getElementById("rodape");
    if (!hero || !final || !footer || !("IntersectionObserver" in window)) return;

    const blocks = new Map<Element, boolean>([[hero, true], [final, false], [footer, false]]);
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) blocks.set(entry.target, entry.isIntersecting);
      setVisible(!Array.from(blocks.values()).some(Boolean) && hero.getBoundingClientRect().bottom <= 0);
    });
    for (const element of blocks.keys()) observer.observe(element);
    return () => observer.disconnect();
  }, []);

  if (!visible && !focused) return null;
  return (
    <div className={styles.fixed}>
      <Link className="button primary" href={localizedHref(locale, ctaFixo.href)} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}>
        {ctaFixo.label} <span aria-hidden="true">→</span>
      </Link>
    </div>
  );
}
