"use client";

import { useEffect, useId, useRef, useState } from "react";
import { glossary, type GlossaryKey } from "../../content/glossary";
import { useLocale } from "./LocaleProvider";

/** Botão "?" com explicação curta para iniciantes. Abre ao passar o mouse, ao focar ou ao tocar. */
export default function Help({ id, label }: { id: GlossaryKey; label: string }) {
  const { locale, t } = useLocale();
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [left, setLeft] = useState(0);
  const root = useRef<HTMLSpanElement>(null);
  const tipId = useId();
  const visible = !dismissed && (open || hovered || focused);

  useEffect(() => {
    if (!visible) return;
    const dismiss = () => {
      setOpen(false);
      setDismissed(true);
    };
    const close = (event: PointerEvent) => {
      if (event.target instanceof Node && !root.current?.contains(event.target)) dismiss();
    };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") dismiss(); };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", escape);
    window.addEventListener("resize", measure);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", escape);
      window.removeEventListener("resize", measure);
    };
  }, [visible]);

  function measure() {
    const box = root.current?.getBoundingClientRect();
    if (!box) return;
    const width = Math.min(280, window.innerWidth - 32);
    setLeft(Math.max(16, Math.min(box.left, window.innerWidth - width - 16)) - box.left);
  }

  return (
    <span className="help" ref={root} onPointerEnter={(event) => {
      if (event.pointerType !== "mouse") return;
      measure();
      setDismissed(false);
      setHovered(true);
    }} onPointerLeave={() => setHovered(false)}>
      <button type="button" className="help-button" aria-label={t("O que é {label}?", { label })}
        aria-expanded={visible} aria-describedby={tipId}
        onFocus={(event) => {
          if (!event.currentTarget.matches(":focus-visible")) return;
          measure();
          setDismissed(false);
          setFocused(true);
        }}
        onBlur={() => { setFocused(false); setOpen(false); }}
        onClick={() => {
          measure();
          setDismissed(open);
          setOpen(!open);
        }}>
        <span aria-hidden="true">?</span>
      </button>
      <span id={tipId} role="tooltip" className="help-tip" hidden={!visible} style={{ left }}>{glossary[locale][id]}</span>
    </span>
  );
}
