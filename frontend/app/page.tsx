import type { Metadata } from "next";
import Alvos from "../components/landing/Alvos";
import ComoFunciona from "../components/landing/ComoFunciona";
import CtaFinal from "../components/landing/CtaFinal";
import CtaFixo from "../components/landing/CtaFixo";
import Dados from "../components/landing/Dados";
import Hero from "../components/landing/Hero";
import PorQue from "../components/landing/PorQue";
import Sobre from "../components/landing/Sobre";
import { metadados } from "../content/landing";

export const metadata: Metadata = {
  title: metadados.titulo,
  description: metadados.descricao,
  openGraph: {
    title: metadados.compartilhamento.titulo,
    description: metadados.compartilhamento.descricao,
    type: "website",
    locale: "pt_BR",
    siteName: "SPHEREye",
  },
};

export default function Home() {
  return (
    <main id="conteudo">
      <Hero />
      <PorQue />
      <ComoFunciona />
      <Alvos />
      <Dados />
      <Sobre />
      <CtaFinal />
      <CtaFixo />
    </main>
  );
}
