import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Página não encontrada" };

export default function NotFound() {
  return (
    <main id="conteudo" className="shell not-found" tabIndex={-1}>
      <h1>Página não encontrada</h1>
      <p>Confira o endereço ou volte à página inicial.</p>
      <Link className="button primary" href="/">Voltar ao início</Link>
    </main>
  );
}
