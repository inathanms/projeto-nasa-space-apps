import { useSyncExternalStore } from "react";
import { A11Y_DEFAULTS, A11Y_KEY, type A11ySettings } from "./a11y-boot";

// Preferências de acessibilidade escolhidas pela pessoa. Ficam no navegador (localStorage) e
// viram atributos data-a11y-* na tag <html>; o CSS em globals.css reage a esses atributos.
export type { A11ySettings };

let current: A11ySettings = A11Y_DEFAULTS;
let loaded = false;
const listeners = new Set<() => void>();

function read(): A11ySettings {
  try {
    const stored: unknown = JSON.parse(window.localStorage.getItem(A11Y_KEY) ?? "null");
    return stored && typeof stored === "object" ? { ...A11Y_DEFAULTS, ...(stored as Partial<A11ySettings>) } : A11Y_DEFAULTS;
  } catch {
    return A11Y_DEFAULTS;
  }
}

/** Escreve os atributos na tag <html>. Só os valores fora do padrão viram atributo. */
export function applyA11y(settings: A11ySettings) {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(settings)) {
    const name = `data-a11y-${key}`;
    if (value === A11Y_DEFAULTS[key as keyof A11ySettings]) root.removeAttribute(name);
    else root.setAttribute(name, String(value));
  }
}

export function setA11y(next: Partial<A11ySettings> | null) {
  current = next === null ? A11Y_DEFAULTS : { ...current, ...next };
  applyA11y(current);
  try {
    if (next === null) window.localStorage.removeItem(A11Y_KEY);
    else window.localStorage.setItem(A11Y_KEY, JSON.stringify(current));
  } catch { /* Sem armazenamento: as escolhas valem só nesta visita. */ }
  listeners.forEach((listener) => listener());
}

export function useA11y() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => {
      if (!loaded) {
        loaded = true;
        current = read();
      }
      return current;
    },
    () => A11Y_DEFAULTS,
  );
}

/** Movimento reduzido, pela opção do site ou pelo ajuste do sistema. Use em rolagens feitas por JS. */
export function reducedMotion() {
  return document.documentElement.getAttribute("data-a11y-motion") === "true"
    || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
