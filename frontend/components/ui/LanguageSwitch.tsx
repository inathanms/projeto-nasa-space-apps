"use client";

import { usePathname } from "next/navigation";
import type { SyntheticEvent } from "react";
import { languageTag, localizedHref } from "../../lib/i18n";
import { useLocale } from "./LocaleProvider";

export default function LanguageSwitch() {
  const pathname = usePathname();
  const { locale, t } = useLocale();
  const next = locale === "en" ? "pt" : "en";
  const label = next === "pt" ? "Português" : "English";

  function destination(path: string) {
    const primary = localizedHref("en", path).split(/[?#]/, 1)[0];
    if (!["/", "/explore/", "/observatory/", "/lab/"].includes(primary)) {
      return next === "pt" ? "/pt/404/" : "/404.html";
    }
    return localizedHref(next, path);
  }

  function updateDestination(event: SyntheticEvent<HTMLAnchorElement>) {
    const { pathname, search, hash } = window.location;
    event.currentTarget.href = destination(pathname + search + hash);
  }

  return (
    <nav className="site-language" aria-label={t("Idioma")}>
      <a href={destination(pathname)} lang={languageTag[next]} hrefLang={languageTag[next]}
        onClick={updateDestination} onAuxClick={updateDestination} onFocus={updateDestination}
        onPointerEnter={updateDestination} onContextMenu={updateDestination}>
        {label}
      </a>
    </nav>
  );
}
