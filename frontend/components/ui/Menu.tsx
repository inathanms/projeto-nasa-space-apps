"use client";

import type { ReactNode } from "react";

export default function Menu({ label, children, className = "site-menu" }: {
  label: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <details className={className}
      onClick={(event) => {
        const link = event.target instanceof Element && event.target.closest("a");
        if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.currentTarget.open = false;
        if (link.origin === location.origin && link.pathname === location.pathname && link.hash) {
          document.getElementById(link.hash.slice(1))?.focus({ preventScroll: true });
        }
      }}
      onBlur={(event) => {
        if (event.relatedTarget instanceof Node && !event.currentTarget.contains(event.relatedTarget)) {
          event.currentTarget.open = false;
        }
      }}
      onKeyDown={(event) => {
        if (event.key !== "Escape" || !event.currentTarget.open) return;
        event.preventDefault();
        event.currentTarget.open = false;
        event.currentTarget.querySelector("summary")?.focus();
      }}>
      <summary>{label}</summary>
      {children}
    </details>
  );
}
