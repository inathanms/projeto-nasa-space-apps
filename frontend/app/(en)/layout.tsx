import type { ReactNode } from "react";
import Site, { siteMetadata } from "../_shared/site";

export { viewport } from "../_shared/site";
export const metadata = siteMetadata("en");

export default function RootLayout({ children }: { children: ReactNode }) {
  return <Site locale="en">{children}</Site>;
}
