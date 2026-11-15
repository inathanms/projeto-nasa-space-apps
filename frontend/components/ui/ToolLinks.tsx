"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { nav } from "../../content/landing";

export default function ToolLinks() {
  const pathname = usePathname().replace(/\/$/, "");
  return nav.ferramentas.map(({ href, label }) => (
    <Link href={href} key={href} aria-current={pathname === href.replace(/\/$/, "") ? "page" : undefined}>
      {label}
    </Link>
  ));
}
