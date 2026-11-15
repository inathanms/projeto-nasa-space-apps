import type { ReactNode } from "react";
import Site, { siteMetadata } from "../_shared/site";

export { viewport } from "../_shared/site";
export const metadata = siteMetadata("pt");

export default function RootLayout({ children }: { children: ReactNode }) {
  return <Site locale="pt">{children}</Site>;
}
