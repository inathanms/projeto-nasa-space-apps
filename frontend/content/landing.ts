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

export const marca = {
  nome: "Oxen",
  nomeDestaque: "Tech",
  subtitulo: "CÉU DO SERTÃO · SPHEREx",
  logoMark: "/brand/logo-oxentech-mark.png",
  logoAlt: "Logo da OxenTech: cacto e boi-constelação sob o céu do sertão",
};

export const nav = {
  rotuloMenu: "Navegação principal",
  menu: "Menu",
  links: [
    { href: "/#por-que", label: "Por que aqui" },
    { href: "/#como-funciona", label: "Como funciona" },
    { href: "/#alvos", label: "Alvos" },
    { href: "/#dados", label: "Dados" },
    { href: "/#sobre", label: "Quem somos" },
  ],
  ferramentas: [
    { href: "/explorar/", label: "Explorador" },
    { href: "/observatorio/", label: "Observatório" },
    { href: "/laboratorio/", label: "Laboratório" },
  ],
  cta: { href: "/explorar/", label: "Explorar o céu" },
};

export const hero = {
  kicker: "1930 · PLUTÃO FOI DESCOBERTO ASSIM",
  titulo: [
    { texto: "Duas fotos." },
    { texto: "Um ponto que ", destaque: "mudou de lugar." },
    { texto: "Uma descoberta histórica." },
  ],
  texto: "Agora as fotos são do SPHEREx, o telescópio infravermelho da NASA. E quem compara é você.",
  exemplo: { href: "/explorar/?alvo=barnard", label: "Ver um exemplo" },
  selos: ["Grátis", "Sem cadastro", "Dados reais da NASA"],
  provas: [
    { forte: "5 alvos", texto: "prontos para começar" },
    { forte: "SPHEREx", texto: "· NASA/IPAC IRSA" },
  ],
  // Placas reais da descoberta de Plutão (Clyde Tombaugh, Observatório Lowell, 1930).
  // Fonte: https://commons.wikimedia.org/wiki/File:Pluto_discovery_plates.png — domínio público (PD US expired).
  // Recortes 360×360 px da mesma região do céu, alinhados pelas estrelas de referência:
  //   23/jan: x 218, y 418 · 29/jan: x 1139, y 420 (na imagem original de 1779×1101).
  // plutao = posição de Plutão no recorte, em fração (0..1).
  fotos: {
    foto1: { titulo: "FOTO 1 · 23 jan 1930", src: "/historico/pluto-1930-01-23.jpg", alt: "Na primeira placa, Plutão está à esquerda entre as estrelas.", plutao: { x: 0.261, y: 0.544 } },
    foto2: { titulo: "FOTO 2 · 29 jan 1930", src: "/historico/pluto-1930-01-29.jpg", alt: "Na segunda placa, o círculo tracejado indica a posição anterior e o círculo laranja mostra Plutão mais à direita.", plutao: { x: 0.742, y: 0.456 } },
    achou: "Plutão!",
    credito: "Placas originais · Clyde Tombaugh, Observatório Lowell, 1930 · domínio público",
    creditoHref: "https://commons.wikimedia.org/wiki/File:Pluto_discovery_plates.png",
  },
};

export const porQue = {
  kicker: "POR QUE AQUI",
  titulo: "O céu que seus olhos não veem",
  lead: "O SPHEREx fotografa o universo em luz infravermelha. A gente transforma esses dados em algo que qualquer curioso consegue explorar.",
  cards: [
    {
      icone: "invisivel" as IconKey,
      titulo: "Veja o invisível",
      texto:
        "Imagens infravermelhas reais, de estrelas frias e poeira que nenhum telescópio comum mostra.",
    },
    {
      icone: "epocas" as IconKey,
      titulo: "Compare épocas",
      texto:
        "Alterne entre fotos do mesmo ponto do céu com meses de diferença e veja o que mudou.",
    },
    {
      icone: "historias" as IconKey,
      titulo: "Histórias prontas",
      texto:
        "Comece pela estrela mais rápida do céu ou pela anã marrom mais fria já encontrada.",
    },
    {
      icone: "cidada" as IconKey,
      titulo: "Ciência cidadã",
      texto:
        "Plutão foi achado comparando fotos. O próximo planeta pode ser achado por você.",
    },
  ],
};

export const comoFunciona = {
  kicker: "COMO FUNCIONA",
  titulo: "Três passos, nenhum telescópio",
  lead: "Você escolhe um ponto do céu, a gente busca as fotos no arquivo da NASA e alinha tudo para você comparar.",
  passos: [
    {
      titulo: "Escolha um alvo",
      texto:
        "Escolha um astro em destaque ou digite as coordenadas de um ponto no céu.",
    },
    {
      titulo: "Compare as épocas",
      texto: "Aperte play e alterne entre fotos tiradas com meses de diferença.",
    },
    {
      titulo: "Descubra",
      texto:
        "Procure pontos que mudaram de posição ou de brilho entre as fotos.",
    },
  ],
};

export const alvosSecao = {
  kicker: "ALVOS EM DESTAQUE",
  titulo: "Comece por aqui",
  lead: "Os alvos escolhidos pelo desafio da NASA, cada um com algo para você perceber.",
  rotuloTag: { movimento: "movimento", brilho: "brilho" } as Record<AlvoTag, string>,
  hrefBase: "/explorar/?alvo=",
  fotoAlt: (nome: string) => `Imagem DSS2 da região de ${nome}`,
  credito: "Imagens DSS2: STScI · Caltech/Palomar POSS-II · UK Schmidt/AAO, via NASA SkyView. Uso educacional, sem fins comerciais.",
};

export const alvos = [
  {
    slug: "barnard",
    nome: "Estrela de Barnard",
    texto: "A estrela que mais anda no nosso céu.",
    tag: "movimento",
  },
  {
    slug: "wise0855",
    nome: "WISE 0855",
    texto: "A anã marrom mais fria conhecida, mais fria que o Polo Norte.",
    tag: "movimento",
  },
  {
    slug: "eps-indi-b",
    nome: "Epsilon Indi B",
    texto: "Duas “estrelas fracassadas” dançando juntas.",
    tag: "movimento",
  },
  {
    slug: "rw-aur",
    nome: "RW Aurigae",
    texto: "Uma estrela jovem que muda de brilho.",
    tag: "brilho",
  },
  {
    slug: "r-dra",
    nome: "R Draconis",
    texto: "Uma estrela que pisca ao longo dos meses.",
    tag: "brilho",
  },
] satisfies { slug: string; nome: string; texto: string; tag: AlvoTag }[];

export const dados = {
  kicker: "DE ONDE VÊM OS DADOS",
  titulo: "Direto do arquivo da NASA",
  lead: "Os recortes reais vêm do arquivo público do SPHEREx no NASA/IPAC IRSA, com data, detector, comprimento de onda e link para o original. Os exemplos educativos simulados são identificados no visor.",
  credito:
    "SPHEREx: NASA / JPL-Caltech / IPAC · IRSA DOI 10.26131/IRSA678 · 10.26131/IRSA662",
  rotuloFluxo: "Caminho dos dados",
  fluxo: [
    { icone: "satelite" as IconKey, titulo: "SPHEREx", texto: "órbita a 700 km" },
    { icone: "arquivo" as IconKey, titulo: "IRSA", texto: "arquivo NASA" },
    { icone: "cacto" as IconKey, titulo: "OxenTech", texto: "alinha e mostra" },
  ],
};

export const sobre = {
  kicker: "QUEM SOMOS",
  titulo: "OxenTech",
  paragrafos: [
    "Somos uma equipe de Aracaju, Sergipe. O nome mistura o “oxente” do nordeste com tecnologia, e o boi do nosso logo é a constelação do Touro, que brilha no céu do sertão.",
    "Acreditamos que olhar para o céu não depende de onde você está, só da curiosidade.",
  ],
};

export const ctaFinal = {
  titulo: "Pronto para olhar para cima?",
  texto: "Escolha uma estrela e veja o que mudou.",
  acoes: [
    nav.cta,
    { href: "/observatorio/", label: "Abrir o observatório" },
    { href: "/laboratorio/", label: "Ajustar a mira no laboratório" },
  ],
};

export const ctaFixo = {
  ...nav.cta,
};

export const footer = {
  esquerda: "© 2026 OxenTech · NASA Space Apps Challenge 2026",
  direita:
    "Dados: NASA/JPL-Caltech/IPAC via IRSA · Projeto independente, sem endosso da NASA",
};

export const metadados = {
  titulo: "Duas fotos. Uma descoberta histórica.",
  descricao:
    "Compare imagens reais do telescópio SPHEREx em épocas diferentes e descubra estrelas que andam e mudam de brilho. NASA Space Apps Challenge 2026.",
};
