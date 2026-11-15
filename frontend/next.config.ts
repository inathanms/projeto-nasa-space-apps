import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";
import { rewrites } from "../vercel.json";

export default function config(phase: string): NextConfig {
  const development = phase === PHASE_DEVELOPMENT_SERVER;
  return {
    output: development ? undefined : "export",
    images: { unoptimized: true },
    trailingSlash: true,
    devIndicators: false,
    experimental: { globalNotFound: true },
    ...(development && {
      async rewrites() {
        return rewrites.map(({ source, destination }) => ({ source: source + "/", destination }));
      },
    }),
  };
}
