import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { metadados } from "@/content/landing";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "700", "800"],
  variable: "--font-inter",
  display: "swap",
  fallback: ["Arial", "sans-serif"],
});

export const metadata: Metadata = {
  title: metadados.titulo,
  description: metadados.descricao,
  icons: { icon: "/brand/logo-oxentech-mark.png" },
};

export const viewport: Viewport = {
  themeColor: "#0b1f22",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
