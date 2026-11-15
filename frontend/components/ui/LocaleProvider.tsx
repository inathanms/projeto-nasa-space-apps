"use client";

import { createContext, useContext, type ReactNode } from "react";
import { localizedHref, translators, type Locale } from "../../lib/i18n";

const LocaleContext = createContext<Locale>("en");

export default function LocaleProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  return <LocaleContext value={locale}>{children}</LocaleContext>;
}

export function useLocale() {
  const locale = useContext(LocaleContext);
  return { locale, t: translators[locale], href: (path: string) => localizedHref(locale, path) };
}
