"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ctaFixo } from "../../content/landing";
import styles from "./landing.module.css";

export default function CtaFixo() {
  const [visible, setVisible] = useState(false);

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

  if (!visible) return null;
  return (
    <div className={styles.fixed}>
      <Link className="button primary" href={ctaFixo.href}>
        {ctaFixo.label} <span aria-hidden="true">→</span>
      </Link>
    </div>
  );
}
