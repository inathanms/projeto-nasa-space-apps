"use client";

import { usePathname } from "next/navigation";
import type { SyntheticEvent } from "react";
import { languageTag, localizedHref, type Locale } from "../../lib/i18n";
import { useLocale } from "./LocaleProvider";
import Menu from "./Menu";

const languages = [
  { locale: "en", label: "English" },
  { locale: "pt", label: "Português" },
] as const;

function Flag({ locale }: { locale: Locale }) {
  return (
    <svg className="language-flag" viewBox={locale === "pt" ? "0 0 20 14" : "0 0 20 13"}
      width="20" height="14" aria-hidden="true" focusable="false">
      {locale === "pt" ? <>
        <rect width="20" height="14" fill="#009b3a" />
        <path d="m2 7 8-5 8 5-8 5Z" fill="#ffdf00" />
        <circle cx="10" cy="7" r="3.2" fill="#002776" />
        <path d="M7 6.3q3.2-.2 5.7 1.8" fill="none" stroke="#fff" strokeWidth=".7" />
      </> : <>
        <rect width="20" height="13" fill="#fff" />
        <path d="M0 .5h20M0 2.5h20M0 4.5h20M0 6.5h20M0 8.5h20M0 10.5h20M0 12.5h20" stroke="#b31942" />
        <path d="M0 0h9v7H0z" fill="#244477" />
        <path d="M1.3 1.5h6.4M2.4 3.5h4.2M1.3 5.5h6.4" stroke="#fff" strokeWidth=".7" strokeDasharray=".6 1.3" />
      </>}
    </svg>
  );
}

function destination(locale: Locale, path: string) {
  const primary = localizedHref("en", path).split(/[?#]/, 1)[0];
  if (!["/", "/explore/", "/observatory/", "/lab/"].includes(primary)) {
    return locale === "pt" ? "/pt/404/" : "/404.html";
  }
  return localizedHref(locale, path);
}

export default function LanguageSwitch() {
  const pathname = usePathname();
  const { locale, t } = useLocale();

  function updateDestination(event: SyntheticEvent<HTMLAnchorElement>, language: Locale) {
    const { pathname, search, hash } = window.location;
    event.currentTarget.href = destination(language, pathname + search + hash);
  }

  return (
    <Menu className="site-language" label={<>
      <svg viewBox="0 0 24 24" width="21" height="21" aria-hidden="true" focusable="false"
        fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="12" cy="12" r="9" />
        <ellipse cx="12" cy="12" rx="4" ry="9" />
        <path d="M3 12h18" />
      </svg>
      <Flag locale={locale} />
      <span className="sr-only">{t("Idioma")}</span>
    </>}>
      <nav aria-label={t("Idioma")}>
        {languages.map(({ locale: language, label }) => language === locale
          ? <span key={language} lang={languageTag[language]} aria-current="true"><Flag locale={language} />{label}</span>
          : <a key={language} href={destination(language, pathname)} lang={languageTag[language]} hrefLang={languageTag[language]}
              onClick={(event) => updateDestination(event, language)} onAuxClick={(event) => updateDestination(event, language)}
              onFocus={(event) => updateDestination(event, language)} onPointerEnter={(event) => updateDestination(event, language)}
              onContextMenu={(event) => updateDestination(event, language)}>
              <Flag locale={language} />{label}
            </a>)}
      </nav>
    </Menu>
  );
}
