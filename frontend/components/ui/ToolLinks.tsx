"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { localizedHref } from "../../lib/i18n";
import { useLocale } from "./LocaleProvider";

export default function ToolLinks({ links }: { links: { href: string; label: string }[] }) {
  const pathname = usePathname();
  const { locale, href } = useLocale();
  return links.map(({ href: path, label }) => (
    <Link href={href(path)} key={path} aria-current={localizedHref(locale, pathname) === href(path) ? "page" : undefined}>
      {label}
    </Link>
  ));
}
