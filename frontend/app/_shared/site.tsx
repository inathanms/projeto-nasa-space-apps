import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import type { ReactNode } from "react";
import Footer from "../../components/ui/Footer";
import Nav from "../../components/ui/Nav";
import LocaleProvider from "../../components/ui/LocaleProvider";
import DiscoveryWidget from "../../components/discovery/DiscoveryWidget";
import { getLanding } from "../../content/landing";
import { languageTag, translators, type Locale } from "../../lib/i18n";
import "../globals.css";

const geist = localFont({
  src: "../fonts/geist-latin.woff2",
  variable: "--font-geist",
  weight: "100 900",
  display: "swap",
});

const deployHostname = process.env.VERCEL_ENV === "preview"
  ? process.env.VERCEL_BRANCH_URL ?? process.env.VERCEL_URL
  : process.env.VERCEL_PROJECT_PRODUCTION_URL;

export function siteMetadata(locale: Locale): Metadata {
  const { marca, metadados } = getLanding(locale);
  return {
    metadataBase: new URL(deployHostname ? `https://${deployHostname}` : "http://localhost:3000"),
    title: { default: "SPHEREye", template: "%s · SPHEREye" },
    description: metadados.descricao,
    icons: { icon: marca.logoIcon },
    other: { "page-type": "software", "site-kind": "software" },
  };
}

export const viewport: Viewport = { viewportFit: "cover", themeColor: "#0b1f22" };

export default function Site({ children, locale }: { children: ReactNode; locale: Locale }) {
  const t = translators[locale];

  return (
    <html lang={languageTag[locale]} data-type="software" className={geist.variable}>
      <body>
        <LocaleProvider locale={locale}>
          <a className="skip" href="#conteudo">{t("Ir para o conteúdo")}</a>
          <Nav locale={locale} />
          {children}
          <Footer locale={locale} />
          <DiscoveryWidget />
        </LocaleProvider>
      </body>
    </html>
  );
}
