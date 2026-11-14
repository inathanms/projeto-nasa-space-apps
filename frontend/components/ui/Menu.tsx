"use client";

import type { ReactNode } from "react";

export default function Menu({ label, children }: { label: string; children: ReactNode }) {
  return (
    <details className="site-menu"
      onClick={(event) => {
        if (event.target instanceof Element && event.target.closest("a")) event.currentTarget.open = false;
      }}
      onKeyDown={(event) => {
        if (event.key !== "Escape" || !event.currentTarget.open) return;
        event.currentTarget.open = false;
        event.currentTarget.querySelector("summary")?.focus();
      }}>
      <summary>{label}</summary>
      {children}
    </details>
  );
}
