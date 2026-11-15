import { englishMessages } from "../content/messages";

export type Locale = "en" | "pt";
export type Message = keyof typeof englishMessages;

export const languageTag = { en: "en-US", pt: "pt-BR" } as const;

type Values = Record<string, string | number>;

export function translator(locale: Locale) {
  return (message: Message, values?: Values): string => {
    const text = locale === "en" ? englishMessages[message] : message;
    return values ? text.replace(/\{(\w+)\}/g, (match, key: string) => String(values[key] ?? match)) : text;
  };
}

const en = translator("en");
const pt = translator("pt");
export const translators = { en, pt };

const routes = {
  explorar: "explore",
  observatorio: "observatory",
  laboratorio: "lab",
} as const;

export function localizedHref(locale: Locale, href: string) {
  if (!href.startsWith("/") || href.startsWith("//")) return href;
  const suffixIndex = href.search(/[?#]/);
  const path = suffixIndex === -1 ? href : href.slice(0, suffixIndex);
  const suffix = suffixIndex === -1 ? "" : href.slice(suffixIndex);
  const segment = path.replace(/^\/pt(?=\/|$)/, "").replace(/^\/|\/$/g, "");
  const route = (Object.entries(routes) as [keyof typeof routes, string][])
    .find(([portuguese, english]) => segment === portuguese || segment === english);
  const localized = route ? (locale === "en" ? route[1] : route[0]) : segment;
  return `${locale === "pt" ? "/pt" : ""}/${localized ? `${localized}/` : ""}${suffix}`;
}

export function forLocales<T>(create: (language: string) => T): Record<Locale, T> {
  return { en: create(languageTag.en), pt: create(languageTag.pt) };
}
