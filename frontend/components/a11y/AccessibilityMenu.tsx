"use client";

import { useEffect, useId, useRef, useState } from "react";
import { accessibilityCopy } from "../../content/accessibility";
import { setA11y, useA11y, type A11ySettings } from "../../lib/a11y";
import { useLocale } from "../ui/LocaleProvider";
import VLibras from "./VLibras";

type Toggle = Exclude<keyof A11ySettings, "text">;

/** Botão "Acessibilidade" do cabeçalho e o painel de preferências. */
export default function AccessibilityMenu() {
  const { locale } = useLocale();
  const copy = accessibilityCopy[locale];
  const settings = useA11y();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  // Libras traduz português; o VLibras só é baixado na primeira vez que a pessoa liga a opção.
  const libras = settings.libras && locale === "pt";
  const [librasLoaded, setLibrasLoaded] = useState(false);
  useEffect(() => { if (libras) setLibrasLoaded(true); }, [libras]);

  // Fonte Atkinson Hyperlegible (feita para baixa visão), baixada só quando a opção é ligada.
  useEffect(() => {
    if (!settings.readable || document.getElementById("a11y-readable-font")) return;
    const link = document.createElement("link");
    link.id = "a11y-readable-font";
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&display=swap";
    document.head.appendChild(link);
  }, [settings.readable]);

  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  const toggles: { key: Toggle; label: string; hint: string; disabled?: boolean }[] = [
    { key: "libras", label: copy.libras, hint: copy.librasHint, disabled: locale !== "pt" },
    { key: "colorblind", label: copy.colorblind, hint: copy.colorblindHint },
    { key: "contrast", label: copy.contrast, hint: copy.contrastHint },
    { key: "motion", label: copy.motion, hint: copy.motionHint },
    { key: "underline", label: copy.underline, hint: copy.underlineHint },
    { key: "readable", label: copy.readable, hint: copy.readableHint },
  ];
  const sizes: [A11ySettings["text"], string][] = [["md", copy.textMd], ["lg", copy.textLg], ["xl", copy.textXl]];

  return (
    <div className="a11y" ref={root}>
      <button ref={button} type="button" className="a11y-button" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((value) => !value)}>
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">
          <circle cx="12" cy="4.5" r="2" fill="currentColor" />
          <path d="M5 8.5l7 1.5 7-1.5M12 10v4.5m0 0l-3 6.5m3-6.5l3 6.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="a11y-button-label">{copy.button}</span>
      </button>

      <section id={panelId} className="a11y-panel" hidden={!open} aria-labelledby={`${panelId}-title`}>
        <header className="a11y-head">
          <h2 id={`${panelId}-title`}>{copy.title}</h2>
          <button type="button" className="a11y-close" aria-label={copy.close} onClick={() => { setOpen(false); button.current?.focus(); }}>×</button>
        </header>
        <p className="a11y-intro">{copy.intro}</p>

        <fieldset className="a11y-size">
          <legend>{copy.text}</legend>
          <div role="radiogroup" aria-label={copy.text}>
            {sizes.map(([value, label]) => (
              <button key={value} type="button" role="radio" aria-checked={settings.text === value} data-size={value}
                onClick={() => setA11y({ text: value })}>
                <span aria-hidden="true">A</span> {label}
              </button>
            ))}
          </div>
        </fieldset>

        <ul className="a11y-list">
          {toggles.map(({ key, label, hint, disabled }) => (
            <li key={key}>
              <button type="button" role="switch" className="a11y-switch" aria-checked={settings[key]} disabled={disabled}
                aria-describedby={`${panelId}-${key}`} onClick={() => setA11y({ [key]: !settings[key] })}>
                <span className="a11y-switch-text">{label}</span>
                <span className="a11y-switch-track" aria-hidden="true"><span /></span>
                <span className="sr-only">{settings[key] ? copy.on : copy.off}</span>
              </button>
              <p id={`${panelId}-${key}`} className="a11y-hint">{hint}</p>
            </li>
          ))}
        </ul>

        <button type="button" className="a11y-reset" onClick={() => setA11y(null)}>{copy.reset}</button>
      </section>

      {librasLoaded && <VLibras enabled={libras} />}
    </div>
  );
}
