import type { Metadata } from "next";
import { localizedHref, translators, type Locale } from "../lib/i18n";
import { getLanding } from "./landing";

export function getRoutes(locale: Locale) {
  const t = translators[locale];
  return {
    explorar: {
      title: t("Explorar o céu"),
      description: t("Percorra as observações de um campo e compare imagens de épocas diferentes."),
    },
    observatorio: {
      title: t("Observatório orbital"),
      description: t("Ajuste a mira de uma cena orbital e registre alvos no diário de bordo."),
    },
    laboratorio: {
      title: t("Laboratório de apontamento"),
      description: t("Gire o globo e incline a linha de visão do telescópio. Use as coordenadas resultantes para buscar um campo no explorador."),
    },
    licencas: {
      title: t("Licenças de código aberto"),
      description: t("Licenças, avisos e créditos dos componentes de terceiros usados pelo SPHEREye."),
    },
  };
}

type Page = "home" | keyof ReturnType<typeof getRoutes>;

export function metadataFor(locale: Locale, page: Page): Metadata {
  const { metadados } = getLanding(locale);
  const route = page === "home"
    ? { title: metadados.titulo, description: metadados.descricao }
    : getRoutes(locale)[page];
  const social = page === "home"
    ? { title: metadados.compartilhamento.titulo, description: metadados.compartilhamento.descricao }
    : route;
  const path = page === "home" ? "/" : `/${page}/`;
  return {
    ...route,
    alternates: {
      canonical: localizedHref(locale, path),
      languages: { en: localizedHref("en", path), "pt-BR": localizedHref("pt", path), "x-default": localizedHref("en", path) },
    },
    openGraph: {
      ...social,
      type: "website",
      url: localizedHref(locale, path),
      locale: locale === "en" ? "en_US" : "pt_BR",
      alternateLocale: locale === "en" ? "pt_BR" : "en_US",
      siteName: "SPHEREye",
      images: [{
        url: `/share/${locale}.jpg`, width: 1200, height: 630,
        alt: translators[locale]("Cartão do SPHEREye com duas fotos históricas de Plutão e convite para explorar o céu."),
      }],
    },
  };
}
