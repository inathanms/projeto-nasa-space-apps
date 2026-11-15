// Todos os textos da landing e a lista de alvos.
// Componentes não devem ter texto hardcoded: editar aqui.

export type IconKey =
  | "invisivel"
  | "epocas"
  | "historias"
  | "cidada"
  | "satelite"
  | "arquivo"
  | "cacto";

export type AlvoTag = "movimento" | "brilho";

import { translators, type Locale } from "../lib/i18n";

export function getLanding(locale: Locale) {
  const t = translators[locale];
  const marca = {
    nome: "Spher",
    nomeDestaque: "Eye",
    subtitulo: "OxenTech · NASA Space Apps Challenge 2026",
    logoMark: "/brand/logo-oxentech-mark.png",
    logoIcon: "/brand/logo-oxentech-icon.png",
    logoAlt: t("Logo da OxenTech: cacto e boi-constelação sob o céu do sertão"),
  };

  const nav = {
    rotuloMenu: t("Navegação principal"),
    menu: "Menu",
    links: [
      { href: "/#por-que", label: t("Por que aqui") },
      { href: "/#como-funciona", label: t("Como funciona") },
      { href: "/#alvos", label: t("Alvos") },
      { href: "/#dados", label: t("Dados") },
      { href: "/#sobre", label: t("Quem somos") },
    ],
    ferramentas: [
      { href: "/explorar/", label: t("Explorador") },
      { href: "/observatorio/", label: t("Observatório") },
      // Laboratório em standby (redundante com o Observatório). A página /laboratorio continua existindo.
    ],
    cta: { href: "/explorar/", label: t("Explorar o céu") },
  };

  const hero = {
    kicker: t("1930 · PLUTÃO FOI DESCOBERTO ASSIM"),
    titulo: [
      { texto: t("Duas fotos.") },
      { texto: t("Um ponto que "), destaque: t("mudou de lugar.") },
      { texto: t("Uma descoberta histórica.") },
    ],
    texto: t("Agora as fotos são do SPHEREx, o telescópio infravermelho da NASA. E quem compara é você."),
    exemplo: { href: "/explorar/?alvo=barnard", label: t("Ver um exemplo") },
    selos: [t("Grátis"), t("Sem cadastro"), t("Dados reais da NASA")],
    provas: [
      { forte: t("5 alvos"), texto: t("prontos para começar") },
      { forte: "SPHEREx", texto: "· NASA/IPAC IRSA" },
    ],
    // Placas reais da descoberta de Plutão (Clyde Tombaugh, Observatório Lowell, 1930).
    // Fonte: https://commons.wikimedia.org/wiki/File:Pluto_discovery_plates.png — domínio público (PD US expired).
    // Recortes 360×360 px da mesma região do céu, alinhados pelas estrelas de referência:
    //   23/jan: x 218, y 418 · 29/jan: x 1139, y 420 (na imagem original de 1779×1101).
    // plutao = posição de Plutão no recorte, em fração (0..1).
    fotos: {
      foto1: { titulo: t("FOTO 1 · 23 jan 1930"), src: "/historico/pluto-1930-01-23.jpg", alt: t("Na primeira placa, Plutão está à esquerda entre as estrelas."), plutao: { x: 0.261, y: 0.544 } },
      foto2: { titulo: t("FOTO 2 · 29 jan 1930"), src: "/historico/pluto-1930-01-29.jpg", alt: t("Na segunda placa, o círculo tracejado indica a posição anterior e o círculo laranja mostra Plutão mais à direita."), plutao: { x: 0.742, y: 0.456 } },
      achou: t("Plutão!"),
      credito: t("Placas originais · Clyde Tombaugh, Observatório Lowell, 1930 · domínio público"),
      creditoHref: "https://commons.wikimedia.org/wiki/File:Pluto_discovery_plates.png",
    },
  };

  const porQue = {
    kicker: t("POR QUE AQUI"),
    titulo: t("O céu que seus olhos não veem"),
    lead: t("O SPHEREx fotografa o universo em luz infravermelha. A gente transforma esses dados em algo que qualquer curioso consegue explorar."),
    cards: [
      {
        icone: "invisivel" as IconKey,
        titulo: t("Veja o “invisível”"),
        texto:
          t("Imagens infravermelhas reais, de estrelas frias e poeira que nenhum telescópio comum mostra."),
      },
      {
        icone: "epocas" as IconKey,
        titulo: t("Compare épocas"),
        texto:
          t("Alterne entre fotos do mesmo ponto do céu com meses de diferença e veja o que mudou."),
      },
      {
        icone: "historias" as IconKey,
        titulo: t("Histórias prontas"),
        texto:
          t("Comece pela estrela mais rápida do céu ou pela anã marrom mais fria já encontrada."),
      },
      {
        icone: "cidada" as IconKey,
        titulo: t("Ciência cidadã"),
        texto:
          t("Plutão foi achado comparando fotos. O próximo planeta pode ser achado por você."),
      },
    ],
  };

  const comoFunciona = {
    kicker: t("COMO FUNCIONA"),
    titulo: t("Três passos, nenhum telescópio"),
    lead: t("Você escolhe um ponto do céu, a gente busca as fotos no arquivo da NASA e alinha tudo para você comparar."),
    passos: [
      {
        titulo: t("Escolha um alvo"),
        texto:
          t("Escolha um astro em destaque ou digite as coordenadas de um ponto no céu."),
      },
      {
        titulo: t("Compare as épocas"),
        texto: t("Aperte play e alterne entre fotos tiradas com meses de diferença."),
      },
      {
        titulo: t("Descubra"),
        texto:
          t("Procure pontos que mudaram de posição ou de brilho entre as fotos."),
      },
    ],
  };

  const alvosSecao = {
    kicker: t("ALVOS EM DESTAQUE"),
    titulo: t("Comece por aqui"),
    lead: t("Os alvos escolhidos pelo desafio da NASA, cada um com algo para você perceber."),
    rotuloTag: { movimento: t("movimento"), brilho: t("brilho") } as Record<AlvoTag, string>,
    hrefBase: "/explorar/?alvo=",
    fotoAlt: (nome: string) => t("Imagem DSS2 da região de {name}", { name: nome }),
    credito: t("Imagens DSS2: STScI · Caltech/Palomar POSS-II · UK Schmidt/AAO, via NASA SkyView. Uso educacional, sem fins comerciais."),
  };

  const alvos = [
    {
      slug: "barnard",
      nome: t("Estrela de Barnard"),
      texto: t("A estrela que mais anda no nosso céu."),
      tag: "movimento",
    },
    {
      slug: "wise0855",
      nome: "WISE 0855",
      texto: t("A anã marrom mais fria conhecida, mais fria que o Polo Norte."),
      tag: "movimento",
    },
    {
      slug: "eps-indi-b",
      nome: "Epsilon Indi B",
      texto: t("Duas “estrelas fracassadas” dançando juntas."),
      tag: "movimento",
    },
    {
      slug: "rw-aur",
      nome: "RW Aurigae",
      texto: t("Uma estrela jovem que muda de brilho."),
      tag: "brilho",
    },
    {
      slug: "r-dra",
      nome: "R Draconis",
      texto: t("Uma estrela que pisca ao longo dos meses."),
      tag: "brilho",
    },
  ] satisfies { slug: string; nome: string; texto: string; tag: AlvoTag }[];

  const dados = {
    kicker: t("DE ONDE VÊM OS DADOS"),
    titulo: t("Direto do arquivo da NASA"),
    lead: t("Os recortes reais vêm do arquivo público do SPHEREx no NASA/IPAC IRSA, com data, detector, comprimento de onda e link para o original. Os exemplos educativos simulados são identificados no visor."),
    credito:
      "SPHEREx: NASA / JPL-Caltech / IPAC · IRSA DOI 10.26131/IRSA678 · 10.26131/IRSA662",
    rotuloFluxo: t("Caminho dos dados"),
    fluxo: [
      { icone: "satelite" as IconKey, titulo: "SPHEREx", texto: t("órbita a 700 km") },
      { icone: "arquivo" as IconKey, titulo: "IRSA", texto: t("arquivo NASA") },
      { icone: "cacto" as IconKey, titulo: "SpherEye", texto: t("alinha e mostra") },
    ],
  };

  const sobre = {
    kicker: t("QUEM SOMOS"),
    titulo: "OxenTech",
    paragrafos: [
      t("Somos uma equipe de Aracaju, Sergipe. O nome mistura o “oxente” do nordeste com tecnologia, e o boi do nosso logo é a constelação do Touro, que brilha no céu do sertão."),
      t("Acreditamos que olhar para o céu não depende de onde você está, só da curiosidade."),
    ],
  };

  const ctaFinal = {
    titulo: t("Pronto para olhar para cima?"),
    texto: t("Escolha uma estrela e veja o que mudou."),
    acoes: [
      nav.cta,
      { href: "/observatorio/", label: t("Abrir o observatório") },
    ],
  };

  const ctaFixo = {
    ...nav.cta,
  };

  const footer = {
    esquerda: "© 2026 OxenTech · NASA Space Apps Challenge 2026",
    direita:
      t("Dados: NASA/JPL-Caltech/IPAC via IRSA · Projeto independente, sem endosso da NASA"),
  };

  const metadados = {
    titulo: t("Duas fotos. Uma descoberta histórica."),
    descricao:
      t("Compare imagens reais do telescópio SPHEREx em épocas diferentes e descubra estrelas que andam e mudam de brilho. NASA Space Apps Challenge 2026."),
    compartilhamento: {
      titulo: t("Explore o céu com o SPHEREye"),
      descricao: t("Compare imagens do telescópio SPHEREx e veja o que mudou entre duas épocas."),
    },
  };
  return { marca, nav, hero, porQue, comoFunciona, alvosSecao, alvos, dados, sobre, ctaFinal, ctaFixo, footer, metadados };
}
