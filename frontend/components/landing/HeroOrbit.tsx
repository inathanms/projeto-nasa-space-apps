"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { useHeroMotion } from "./HeroMotion";
import styles from "./landing.module.css";

export default function HeroOrbit({ children }: { children: ReactNode }) {
  const orbit = useRef<HTMLDivElement>(null);
  const { paused } = useHeroMotion();

  useEffect(() => {
    const element = orbit.current;
    if (!element) return;

    const observer = new IntersectionObserver(([entry]) => {
      element.dataset.visible = String(entry.isIntersecting);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div className={styles.heroOrbit} ref={orbit} data-paused={paused}>
      <div className={styles.heroSatellite}>{children}</div>
    </div>
  );
}
