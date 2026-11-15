import type { Locale } from "../lib/i18n";

// Fichas dos alvos do observatório: aparecem ao clicar no card do diário de bordo.
// Mantenha os textos curtos e para iniciantes. Revise números antes de publicar.

export type TargetInfo = {
  tipo: string;
  constelacao: string;
  distancia?: string;
  descoberta?: { quem: string; quando: string; como: string };
  historia: string;
  curiosidade?: string;
  oQueVer: string;
};

const pt: Record<string, TargetInfo> = {
  barnard: {
    tipo: "Anã vermelha",
    constelacao: "Ofiúco (Ophiuchus)",
    distancia: "cerca de 6 anos-luz",
    descoberta: {
      quem: "Edward Emerson Barnard",
      quando: "1916",
      como: "Comparando fotografias do céu tiradas com anos de diferença, ele notou que a estrela tinha se deslocado muito mais do que qualquer outra.",
    },
    historia: "É a estrela isolada mais próxima do Sol depois do sistema Alpha Centauri. Por décadas foi alvo de buscas por planetas, com vários alarmes falsos, até que planetas pequenos foram confirmados ao seu redor em 2024 e 2025.",
    curiosidade: "É a estrela com maior movimento próprio conhecido: anda no céu o equivalente ao tamanho da Lua cheia a cada cerca de 180 anos.",
    oQueVer: "Movimento: entre as épocas ela muda de posição em relação às estrelas de fundo.",
  },
  wise0855: {
    tipo: "Anã marrom (uma “estrela fracassada”)",
    constelacao: "Hidra (Hydra)",
    distancia: "cerca de 7,4 anos-luz",
    descoberta: {
      quem: "Kevin Luhman",
      quando: "2014",
      como: "Encontrada nos dados do telescópio espacial infravermelho WISE e confirmada com o Spitzer, ambos da NASA.",
    },
    historia: "É um dos vizinhos mais próximos do Sol, mas é tão fria e apagada que só foi achada no século XXI, e só em infravermelho. O telescópio James Webb detectou vapor d’água em sua atmosfera.",
    curiosidade: "Sua temperatura fica perto de 0 °C, parecida com a de um dia de inverno aqui na Terra. Para uma “estrela”, isso é gelado.",
    oQueVer: "Movimento: por estar muito perto, ela se desloca visivelmente entre as épocas.",
  },
  "eps-indi-b": {
    tipo: "Par de anãs marrons",
    constelacao: "Índio (Indus)",
    distancia: "cerca de 12 anos-luz",
    descoberta: {
      quem: "Equipe de Ralf-Dieter Scholz",
      quando: "2003",
      como: "Identificada pelo movimento no céu em levantamentos fotográficos. Em 2004 descobriu-se que eram duas anãs marrons orbitando uma à outra.",
    },
    historia: "As duas anãs marrons orbitam a estrela Epsilon Indi A, visível a olho nu no céu do hemisfério sul. Em 2024 o James Webb fotografou diretamente um planeta gigante ao redor dessa estrela.",
    curiosidade: "Por uma década foi o par de anãs marrons mais próximo conhecido. Como as duas orbitam uma à outra, dá para medir suas massas, algo raro para esse tipo de objeto.",
    oQueVer: "Movimento: a fonte se desloca ligeiramente para a esquerda e para baixo entre as épocas.",
  },
  "rw-aur": {
    tipo: "Estrela jovem (tipo T Tauri), em sistema duplo",
    constelacao: "Cocheiro (Auriga)",
    distancia: "cerca de 500 anos-luz",
    historia: "Tem só alguns milhões de anos, um bebê em escala estelar, e ainda está cercada pelo disco de gás e poeira de onde podem nascer planetas. Desde 2010 ela passa por apagões profundos, provavelmente causados por poeira desse disco passando na frente da estrela.",
    curiosidade: "Estudá-la ajuda a entender como era o Sol logo depois de nascer.",
    oQueVer: "Brilho: compare quão intensa ela aparece em cada época.",
  },
  "r-dra": {
    tipo: "Gigante vermelha variável (tipo Mira)",
    constelacao: "Dragão (Draco)",
    historia: "Estrelas do tipo Mira estão no fim da vida: incham e encolhem em ciclos regulares, mudando muito de brilho. R Draconis completa um ciclo em cerca de 8 meses.",
    curiosidade: "No máximo pode ser vista com binóculos; no mínimo fica centenas de vezes mais fraca.",
    oQueVer: "Brilho: o mesmo ponto pode parecer bem mais forte ou mais fraco entre as épocas.",
  },
  m101: {
    tipo: "Galáxia espiral (Galáxia do Cata-vento)",
    constelacao: "Ursa Maior",
    distancia: "cerca de 21 milhões de anos-luz",
    descoberta: {
      quem: "Pierre Méchain",
      quando: "1781",
      como: "Observada ao telescópio e incluída por Charles Messier em seu famoso catálogo de objetos do céu profundo.",
    },
    historia: "É maior que a Via Láctea e é vista de frente, o que mostra bem seus braços espirais. Duas supernovas brilhantes explodiram nela recentemente: SN 2011fe e SN 2023ixf.",
    curiosidade: "A luz que você está vendo saiu dela antes de existirem seres humanos na Terra.",
    oQueVer: "Contexto: galáxias não se movem visivelmente em poucos anos; a diferença entre épocas costuma ser estrelas da nossa própria galáxia na frente.",
  },
};

const en: Record<string, TargetInfo> = {
  barnard: {
    tipo: "Red dwarf",
    constelacao: "Ophiuchus",
    distancia: "about 6 light-years",
    descoberta: {
      quem: "Edward Emerson Barnard",
      quando: "1916",
      como: "By comparing photographs of the sky taken years apart, he noticed the star had moved much farther than any other.",
    },
    historia: "It is the closest single star to the Sun after the Alpha Centauri system. For decades it was searched for planets, with several false alarms, until small planets were confirmed around it in 2024 and 2025.",
    curiosidade: "It has the largest known proper motion of any star: it crosses a full Moon's width of sky about every 180 years.",
    oQueVer: "Motion: between epochs it shifts position relative to the background stars.",
  },
  wise0855: {
    tipo: "Brown dwarf (a “failed star”)",
    constelacao: "Hydra",
    distancia: "about 7.4 light-years",
    descoberta: {
      quem: "Kevin Luhman",
      quando: "2014",
      como: "Found in data from NASA's WISE infrared space telescope and confirmed with Spitzer, also from NASA.",
    },
    historia: "It is one of the Sun's closest neighbors, yet so cold and faint that it was only found in the 21st century, and only in infrared. The James Webb telescope detected water vapor in its atmosphere.",
    curiosidade: "Its temperature is close to 0 °C (32 °F), like a winter day here on Earth. For a “star”, that is freezing.",
    oQueVer: "Motion: because it is so close, it visibly shifts between epochs.",
  },
  "eps-indi-b": {
    tipo: "Pair of brown dwarfs",
    constelacao: "Indus",
    distancia: "about 12 light-years",
    descoberta: {
      quem: "Ralf-Dieter Scholz's team",
      quando: "2003",
      como: "Identified by its motion across the sky in photographic surveys. In 2004 it turned out to be two brown dwarfs orbiting each other.",
    },
    historia: "The two brown dwarfs orbit the star Epsilon Indi A, visible to the naked eye from the southern hemisphere. In 2024 James Webb directly imaged a giant planet around that star.",
    curiosidade: "For a decade it was the closest known pair of brown dwarfs. Because they orbit each other, their masses can be measured, which is rare for this kind of object.",
    oQueVer: "Motion: the source shifts slightly left and down between epochs.",
  },
  "rw-aur": {
    tipo: "Young star (T Tauri type), in a binary system",
    constelacao: "Auriga",
    distancia: "about 500 light-years",
    historia: "It is only a few million years old, a baby on stellar scales, and is still surrounded by the disk of gas and dust where planets can form. Since 2010 it has gone through deep dimming events, probably caused by dust from that disk passing in front of the star.",
    curiosidade: "Studying it helps us understand what the Sun was like right after it was born.",
    oQueVer: "Brightness: compare how bright it appears in each epoch.",
  },
  "r-dra": {
    tipo: "Variable red giant (Mira type)",
    constelacao: "Draco",
    historia: "Mira-type stars are near the end of their lives: they swell and shrink in regular cycles, changing brightness a lot. R Draconis completes a cycle in about 8 months.",
    curiosidade: "At its brightest it can be seen with binoculars; at its faintest it is hundreds of times dimmer.",
    oQueVer: "Brightness: the same point can look much stronger or weaker between epochs.",
  },
  m101: {
    tipo: "Spiral galaxy (Pinwheel Galaxy)",
    constelacao: "Ursa Major",
    distancia: "about 21 million light-years",
    descoberta: {
      quem: "Pierre Méchain",
      quando: "1781",
      como: "Observed through a telescope and added by Charles Messier to his famous catalog of deep-sky objects.",
    },
    historia: "It is larger than the Milky Way and seen face-on, which shows its spiral arms clearly. Two bright supernovae exploded in it recently: SN 2011fe and SN 2023ixf.",
    curiosidade: "The light you are seeing left it before there were humans on Earth.",
    oQueVer: "Context: galaxies do not visibly move in a few years; differences between epochs are usually stars from our own galaxy in the foreground.",
  },
};

export const targetInfo: Record<Locale, Record<string, TargetInfo>> = { pt, en };
