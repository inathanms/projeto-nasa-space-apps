import { Suspense } from "react";
import type { Metadata } from "next";
import { explorar } from "@/content/explorar";
import Explorador from "@/components/explorar/Explorador";

export const metadata: Metadata = {
  title: explorar.metaTitulo,
};

// useSearchParams (?alvo=) exige Suspense no export estático.
export default function ExplorarPage() {
  return (
    <Suspense fallback={<div className="bg-universo" style={{ minHeight: "100dvh" }} />}>
      <Explorador />
    </Suspense>
  );
}
