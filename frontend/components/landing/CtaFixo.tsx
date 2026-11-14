"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ctaFixo, marca } from "@/content/landing";
import CtaLabel from "./CtaLabel";
import s from "./landing.module.css";

// Barra com o CTA que aparece depois que o hero sai da tela
// e some quando o CTA final já está visível (evita botão duplicado).
export default function CtaFixo() {
  const [visivel, setVisivel] = useState(false);

  useEffect(() => {
    const hero = document.getElementById("inicio");
    const final = document.getElementById("cta-final");
    if (!hero || !("IntersectionObserver" in window)) return;

    let heroVisivel = true;
    let finalVisivel = false;
    const atualizar = () => setVisivel(!heroVisivel && !finalVisivel);

    const obs = new IntersectionObserver((entradas) => {
      for (const e of entradas) {
        if (e.target === hero) heroVisivel = e.isIntersecting;
        if (e.target === final) finalVisivel = e.isIntersecting;
      }
      atualizar();
    });
    obs.observe(hero);
    if (final) obs.observe(final);
    return () => obs.disconnect();
  }, []);

  return (
    <div className={`${s.ctaFixo} ${visivel ? s.ctaFixoOn : ""}`} aria-hidden={!visivel}>
      <div className={s.ctaFixoInner}>
        <span className={s.ctaFixoMarca}>
          <img src={marca.logoMark} alt="" width={32} height={32} />
          <span>{ctaFixo.texto}</span>
        </span>
        <Link
          href={ctaFixo.cta.href}
          className={`${s.btn} ${s.btnPrimary} ${s.ctaFixoBtn}`}
          tabIndex={visivel ? 0 : -1}
        >
          <CtaLabel label={ctaFixo.cta.label} />
        </Link>
      </div>
    </div>
  );
}
