"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { localizedHref } from "../../lib/i18n";
import { useLocale } from "./LocaleProvider";

// Nas telas de ferramenta a pessoa já está explorando: o atalho "Explorar o céu" some do cabeçalho.
const TOOL_ROUTES = ["/explorar/", "/observatorio/"];

export default function HeaderCta({ href: path, label }: { href: string; label: string }) {
  const { locale, href } = useLocale();
  // localizedHref normaliza a rota atual para o idioma (ex.: /explore/ ↔ /explorar/).
  const here = localizedHref(locale, usePathname());
  if (TOOL_ROUTES.some((route) => localizedHref(locale, route) === here)) return null;
  return (
    <Link className="button primary header-cta" href={href(path)}>
      {label} <span aria-hidden="true">→</span>
    </Link>
  );
}
