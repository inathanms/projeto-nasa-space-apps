import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import type { ReactNode } from "react";
import Footer from "../components/ui/Footer";
import Nav from "../components/ui/Nav";
import { marca, metadados } from "../content/landing";
import "./globals.css";

const geist = localFont({
  src: "./fonts/geist-latin.woff2",
  variable: "--font-geist",
  weight: "100 900",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "SPHEREye", template: "%s · SPHEREye" },
  description: metadados.descricao,
  icons: { icon: marca.logoMark },
  other: { "page-type": "software", "site-kind": "software" },
};

export const viewport: Viewport = { viewportFit: "cover", themeColor: "#0b1f22" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" data-type="software" className={geist.variable}>
      <body>
        <a className="skip" href="#conteudo">Ir para o conteúdo</a>
        <Nav />
        {children}
        <Footer />
      </body>
    </html>
  );
}
