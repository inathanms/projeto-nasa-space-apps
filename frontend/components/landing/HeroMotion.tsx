"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import styles from "./landing.module.css";

const HeroMotionContext = createContext({ paused: false, toggle: () => {} });

export function useHeroMotion() {
  return useContext(HeroMotionContext);
}

export default function HeroMotion({ children }: { children: ReactNode }) {
  const [paused, setPaused] = useState(false);
  return (
    <HeroMotionContext value={{ paused, toggle: () => setPaused((previous) => !previous) }}>
      {children}
    </HeroMotionContext>
  );
}

export function HeroMotionToggle() {
  const { paused, toggle } = useHeroMotion();
  return (
    <button type="button" className={`button secondary ${styles.heroMotionToggle}`} onClick={toggle} aria-controls="arte-hero">
      {paused ? "Retomar animações" : "Pausar animações"}
    </button>
  );
}
