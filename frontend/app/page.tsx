import Nav from "@/components/landing/Nav";
import Hero from "@/components/landing/Hero";
import PorQue from "@/components/landing/PorQue";
import ComoFunciona from "@/components/landing/ComoFunciona";
import Alvos from "@/components/landing/Alvos";
import Dados from "@/components/landing/Dados";
import Sobre from "@/components/landing/Sobre";
import CtaFinal from "@/components/landing/CtaFinal";
import Footer from "@/components/landing/Footer";
import CtaFixo from "@/components/landing/CtaFixo";

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <PorQue />
        <ComoFunciona />
        <Alvos />
        <Dados />
        <Sobre />
        <CtaFinal />
      </main>
      <Footer />
      <CtaFixo />
    </>
  );
}
