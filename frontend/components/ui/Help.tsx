"use client";

import { useEffect, useId, useRef, useState } from "react";
import { glossary, type GlossaryKey } from "../../content/glossary";
import { useLocale } from "./LocaleProvider";

/** Botão "?" com explicação curta para iniciantes. Abre ao passar o mouse, ao focar ou ao tocar. */
export default function Help({ id, label }: { id: GlossaryKey; label: string }) {
  const { locale, t } = useLocale();
  const [open, setOpen] = useState(false);
  const [alignRight, setAlignRight] = useState(false);
  const root = useRef<HTMLSpanElement>(null);
  const tipId = useId();

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  // Abre a caixa para o lado com mais espaço, para não sair da tela.
  function measure() {
    const box = root.current?.getBoundingClientRect();
    if (box) setAlignRight(box.left > window.innerWidth / 2);
  }

  return (
    <span className="help" ref={root} data-open={open} data-align={alignRight ? "right" : "left"}
      onPointerEnter={measure} onFocus={measure}>
      <button type="button" className="help-button" aria-label={t("O que é {label}?", { label })} aria-expanded={open} aria-describedby={tipId}
        onClick={() => { measure(); setOpen((value) => !value); }}>
        ?
      </button>
      <span id={tipId} role="tooltip" className="help-tip">{glossary[locale][id]}</span>
    </span>
  );
}
