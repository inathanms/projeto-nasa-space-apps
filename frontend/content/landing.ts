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

export type Alvo = {
  slug: string;
  nome: string;
  texto: string;
  tag: AlvoTag;
  /** Ascensão reta em graus (J2000). null = ainda não confirmado. */
  raDeg: number | null;
  /** Declinação em graus (J2000). null = ainda não confirmado. */
  decDeg: number | null;
};

export const marca = {
  nome: "Oxen",
  nomeDestaque: "Tech",
  subtitulo: "CÉU DO SERTÃO · SPHEREx",
  logoMark: "/brand/logo-oxentech-mark.png",
  logoAlt: "Logo da OxenTech: cacto e boi-constelação sob o céu do sertão",
};

export const nav = {
  rotuloMenu: "Navegação principal",
  links: [
    { href: "#por-que", label: "Por que aqui" },
    { href: "#como-funciona", label: "Como funciona" },
    { href: "#alvos", label: "Alvos" },
    { href: "#dados", label: "Dados" },
    { href: "#sobre", label: "Quem somos" },
  ],
  cta: { href: "/explorar", label: "Aceitar o desafio" },
};

export const hero = {
  kicker: "1930 · PLUTÃO FOI DESCOBERTO ASSIM",
  titulo: [
    { texto: "Duas fotos." },
    { texto: "Um ponto que ", destaque: "mudou de lugar." },
    { texto: "Uma descoberta histórica." },
  ],
  texto: "Agora as fotos são do SPHEREx, o telescópio infravermelho da NASA. E quem compara é você.",
  cta: { href: "/explorar", label: "Explorar o céu" },
  selos: ["Grátis", "Sem cadastro", "Dados reais da NASA"],
  provas: [
    { icone: "estrela" as const, forte: "5 alvos", texto: "prontos para começar" },
    { icone: "satelite" as const, forte: "SPHEREx", texto: "· NASA/IPAC IRSA" },
  ],
  // Placas reais da descoberta de Plutão (Clyde Tombaugh, Observatório Lowell, 1930).
  // Fonte: https://commons.wikimedia.org/wiki/File:Pluto_discovery_plates.png — domínio público (PD US expired).
  // Recortes 360×360 px da mesma região do céu, alinhados pelas estrelas de referência:
  //   23/jan: x 218, y 418 · 29/jan: x 1139, y 420 (na imagem original de 1779×1101).
  // plutao = posição de Plutão no recorte, em fração (0..1).
  fotos: {
    rotulo: "Placas originais da descoberta de Plutão, 23 e 29 de janeiro de 1930: Plutão mudou de lugar entre as estrelas",
    foto1: { titulo: "FOTO 1 · 23 jan 1930", src: "/historico/pluto-1930-01-23.jpg", plutao: { x: 0.261, y: 0.544 } },
    foto2: { titulo: "FOTO 2 · 29 jan 1930", src: "/historico/pluto-1930-01-29.jpg", plutao: { x: 0.742, y: 0.456 } },
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
        "Clique num astro em destaque, busque pelo nome ou digite as coordenadas.",
    },
    {
      titulo: "Compare as épocas",
      texto: "Aperte play e alterne entre fotos tiradas com meses de diferença.",
    },
    {
      titulo: "Descubra",
      texto:
        "O que pulou de lugar está se movendo. O que mudou de brilho está pulsando.",
    },
  ],
};

export const alvosSecao = {
  kicker: "ALVOS EM DESTAQUE",
  titulo: "Comece por aqui",
  lead: "Os alvos escolhidos pelo desafio da NASA, cada um com algo para você perceber.",
  rotuloTag: { movimento: "movimento", brilho: "brilho" } as Record<AlvoTag, string>,
  hrefBase: "/explorar?alvo=",
  cardCta: "Explorar",
  // Fotos reais de cada alvo: Digitized Sky Survey 2 (placas azul + vermelha combinadas),
  // recortes 9′ × 6,4′ centrados nas coordenadas do alvo, obtidos via NASA SkyView.
  // Arquivos em public/alvos/<slug>.jpg
  fotoSelo: "Foto real · DSS2",
  fotoAlt: (nome: string) => `Foto real da região do céu onde fica ${nome}`,
  fotoNota: {
    barnard: "Ela aparece duas vezes, laranja e azul: as placas foram feitas em anos diferentes e ela andou entre uma e outra. O círculo marca onde ela estava no ano 2000.",
    wise0855: "Ela está bem no centro, mas é invisível em luz visível: só aparece no infravermelho.",
    "eps-indi-b": "O brilho com anéis à direita é Epsilon Indi A. O par de anãs marrons é fraco demais para a luz visível.",
    "rw-aur": "A estrela no centro da foto é RW Aurigae.",
    "r-dra": "A estrela laranja no centro é R Draconis, uma gigante vermelha.",
  } as Record<string, string>,
  credito:
    "Fotos dos alvos: Digitized Sky Survey 2 (STScI · Caltech/Palomar POSS-II · UK Schmidt/AAO), via NASA SkyView. Uso educacional, sem fins comerciais.",
};

export const alvos: Alvo[] = [
  {
    slug: "barnard",
    nome: "Estrela de Barnard",
    texto: "A estrela que mais anda no nosso céu.",
    tag: "movimento",
    raDeg: 269.4521,
    decDeg: 4.6934,
  },
  {
    slug: "wise0855",
    nome: "WISE 0855",
    texto: "A anã marrom mais fria conhecida, mais fria que o Polo Norte.",
    tag: "movimento",
    raDeg: 133.7951,
    decDeg: -7.2451,
  },
  {
    slug: "eps-indi-b",
    nome: "Epsilon Indi B",
    texto: "Duas “estrelas fracassadas” dançando juntas.",
    tag: "movimento",
    raDeg: 331.0438, // aproximado (22h04m10.5s) — TODO: P4/P5 confirmar no SIMBAD; alto movimento próprio
    decDeg: -56.7828, // aproximado (−56°46′58″) — TODO: confirmar
  },
  {
    slug: "rw-aur",
    nome: "RW Aurigae",
    texto: "Uma estrela jovem que muda de brilho.",
    tag: "brilho",
    raDeg: 76.9564, // aproximado (05h07m49.5s) — TODO: P4/P5 confirmar no SIMBAD
    decDeg: 30.4014, // aproximado (+30°24′05″) — TODO: confirmar
  },
  {
    slug: "r-dra",
    nome: "R Draconis",
    texto: "Uma estrela que pisca ao longo dos meses.",
    tag: "brilho",
    raDeg: 248.1674, // aproximado (16h32m40.2s) — TODO: P4/P5 confirmar no SIMBAD
    decDeg: 66.755, // aproximado (+66°45′18″) — TODO: confirmar
  },
];

export const dados = {
  kicker: "DE ONDE VÊM OS DADOS",
  titulo: "Direto do arquivo da NASA",
  lead: "Cada imagem vem do arquivo público do SPHEREx no NASA/IPAC IRSA, com data, detector, comprimento de onda e link para o original. Nada é simulado.",
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
  nota: "Leva menos de um minuto. Não precisa saber astronomia.",
  cta: { href: "/explorar", label: "Explorar o céu" },
};

export const ctaFixo = {
  texto: "Tem estrela se mexendo agora mesmo no céu.",
  cta: { href: "/explorar", label: "Explorar o céu" },
};

export const footer = {
  esquerda: "© 2026 OxenTech · NASA Space Apps Challenge 2026",
  direita:
    "Dados: NASA/JPL-Caltech/IPAC via IRSA · Projeto independente, sem endosso da NASA",
};

export const metadados = {
  titulo: "OxenTech · Do sertão, veja o céu se mover",
  descricao:
    "Compare imagens reais do telescópio SPHEREx em épocas diferentes e descubra estrelas que andam e mudam de brilho. NASA Space Apps Challenge 2026.",
};
