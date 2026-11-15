import type { Locale } from "../lib/i18n";

// Fichas dos alvos do observatório: aparecem ao clicar no card do diário de bordo.
// Mantenha os textos curtos e para iniciantes. Revise números antes de publicar.

export type TargetInfo = {
  tipo: string;
  constelacao: string;
  distancia?: string;
  descoberta?: { quem: string; quando: string; como: string };
  historia: string;
  curiosidades?: string[];
  /** Sem este campo, a ficha usa a nota de observação do preset (presetFacts). */
  oQueVer?: string;
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
    curiosidades: ["É a estrela com maior movimento próprio conhecido: anda no céu o equivalente ao tamanho da Lua cheia a cada cerca de 180 anos."],
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
    curiosidades: ["Sua temperatura fica perto de 0 °C, parecida com a de um dia de inverno aqui na Terra. Para uma “estrela”, isso é gelado."],
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
    curiosidades: ["Por uma década foi o par de anãs marrons mais próximo conhecido. Como as duas orbitam uma à outra, dá para medir suas massas, algo raro para esse tipo de objeto."],
    oQueVer: "Movimento: a fonte se desloca ligeiramente para a esquerda e para baixo entre as épocas.",
  },
  "rw-aur": {
    tipo: "Estrela jovem (tipo T Tauri), em sistema duplo",
    constelacao: "Cocheiro (Auriga)",
    distancia: "cerca de 500 anos-luz",
    historia: "Tem só alguns milhões de anos, um bebê em escala estelar, e ainda está cercada pelo disco de gás e poeira de onde podem nascer planetas. Desde 2010 ela passa por apagões profundos, provavelmente causados por poeira desse disco passando na frente da estrela.",
    curiosidades: ["Estudá-la ajuda a entender como era o Sol logo depois de nascer."],
    oQueVer: "Brilho: compare quão intensa ela aparece em cada época.",
  },
  "r-dra": {
    tipo: "Gigante vermelha variável (tipo Mira)",
    constelacao: "Dragão (Draco)",
    historia: "Estrelas do tipo Mira estão no fim da vida: incham e encolhem em ciclos regulares, mudando muito de brilho. R Draconis completa um ciclo em cerca de 8 meses.",
    curiosidades: ["No máximo pode ser vista com binóculos; no mínimo fica centenas de vezes mais fraca."],
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
    curiosidades: [
      "A luz que você está vendo saiu dela antes de existirem seres humanos na Terra.",
      "Tem cerca de 170 mil anos-luz de diâmetro, quase o dobro da Via Láctea.",
      "A supernova SN 2011fe foi uma das mais próximas do seu tipo em décadas e chegou a ser vista com binóculos.",
    ],
    oQueVer: "Contexto: galáxias não se movem visivelmente em poucos anos; a diferença entre épocas costuma ser estrelas da nossa própria galáxia na frente.",
  },
  m1: {
    tipo: "Remanescente de supernova (Nebulosa do Caranguejo)",
    constelacao: "Touro (Taurus)",
    distancia: "cerca de 6.500 anos-luz",
    descoberta: {
      quem: "John Bevis; depois Charles Messier",
      quando: "1731 · 1758",
      como: "Messier a encontrou enquanto procurava a volta do cometa Halley. Para não confundir de novo nuvens fixas com cometas, começou seu famoso catálogo, e ela virou o número 1.",
    },
    historia: "É o que sobrou de uma estrela que explodiu e foi vista da Terra em 1054. Astrônomos chineses registraram uma “estrela convidada” tão brilhante que ficou visível de dia por 23 dias.",
    curiosidades: [
      "O nome “Caranguejo” vem de um desenho de 1844 do astrônomo Lord Rosse, que achou a forma parecida com o bicho.",
      "No centro gira um pulsar: uma estrela de nêutrons de uns 20 km que dá cerca de 30 voltas por segundo.",
      "A nuvem ainda se expande a cerca de 1.500 km por segundo.",
    ],
  },
  m8: {
    tipo: "Nebulosa de formação estelar (Nebulosa da Lagoa)",
    constelacao: "Sagitário (Sagittarius)",
    distancia: "cerca de 4.000 anos-luz",
    descoberta: {
      quem: "Giovanni Battista Hodierna",
      quando: "antes de 1654",
      como: "Registrada como uma mancha nebulosa ao telescópio; Messier a incluiu no catálogo em 1764.",
    },
    historia: "É um berçário de estrelas: gás de hidrogênio aceso pela radiação de estrelas jovens e quentes. O “lago” escuro que dá o nome é uma faixa de poeira que corta a nuvem.",
    curiosidades: [
      "Em céu escuro dá para vê-la a olho nu, como uma manchinha acima do “bule” de Sagitário.",
      "No céu ela ocupa uma área maior que a Lua cheia.",
      "Tem pequenas nuvens escuras e densas, os glóbulos de Bok, onde novas estrelas podem estar se formando agora.",
    ],
  },
  m16: {
    tipo: "Nebulosa com aglomerado de estrelas (Nebulosa da Águia)",
    constelacao: "Serpente (Serpens)",
    distancia: "cerca de 7.000 anos-luz",
    descoberta: {
      quem: "Philippe Loys de Chéseaux",
      quando: "1745–1746",
      como: "Ele viu o aglomerado de estrelas; Messier, em 1764, notou a nebulosidade ao redor.",
    },
    historia: "Ficou famosa em 1995 com a foto do Hubble chamada “Pilares da Criação”: colunas de gás e poeira onde estrelas estão nascendo. Em 2022, o James Webb refez a foto em infravermelho.",
    curiosidades: [
      "Cada pilar tem alguns anos-luz de altura: dentro dele caberia o Sistema Solar milhares de vezes.",
      "Em infravermelho, como o do SPHEREx, a poeira fica mais transparente e aparecem estrelas escondidas dentro dos pilares.",
      "A radiação das estrelas jovens vizinhas está aos poucos “evaporando” os pilares.",
    ],
  },
  m27: {
    tipo: "Nebulosa planetária (Nebulosa do Haltere)",
    constelacao: "Raposa (Vulpecula)",
    distancia: "cerca de 1.360 anos-luz",
    descoberta: {
      quem: "Charles Messier",
      quando: "1764",
      como: "Foi a primeira nebulosa planetária a ser descoberta.",
    },
    historia: "É o gás expelido por uma estrela parecida com o Sol no fim da vida. O núcleo que sobrou, uma anã branca muito quente, faz esse gás brilhar.",
    curiosidades: [
      "“Nebulosa planetária” não tem nada a ver com planetas: o nome veio de William Herschel, porque ao telescópio elas pareciam discos de planetas.",
      "Daqui a uns 5 bilhões de anos, o Sol deve formar uma nebulosa parecida.",
      "Tem esse nome porque lembra um haltere de academia.",
    ],
  },
  m31: {
    tipo: "Galáxia espiral (Galáxia de Andrômeda)",
    constelacao: "Andrômeda",
    distancia: "cerca de 2,5 milhões de anos-luz",
    descoberta: {
      quem: "Abd al-Rahman al-Sufi",
      quando: "964",
      como: "O astrônomo persa a descreveu como uma “pequena nuvem” no seu Livro das Estrelas Fixas, séculos antes do telescópio.",
    },
    historia: "Até os anos 1920 muitos achavam que ela era uma nuvem dentro da Via Láctea. Em 1923, Edwin Hubble encontrou nela uma estrela variável que permitiu medir a distância, e provou que era outra galáxia. O Universo ficou muito maior da noite para o dia.",
    curiosidades: [
      "É uma das coisas mais distantes que dá para ver a olho nu.",
      "No céu, ela ocupa cerca de 3°, uma área equivalente a umas seis Luas cheias lado a lado. Só não vemos tudo porque as bordas são fracas.",
      "Ela e a Via Láctea estão se aproximando e podem se fundir daqui a alguns bilhões de anos.",
    ],
  },
  m42: {
    tipo: "Nebulosa de formação estelar (Nebulosa de Órion)",
    constelacao: "Órion",
    distancia: "cerca de 1.350 anos-luz",
    descoberta: {
      quem: "Nicolas-Claude Fabri de Peiresc",
      quando: "1610",
      como: "É o primeiro registro conhecido dela feito com telescópio. A olho nu, ela já era vista como uma “estrela” borrada.",
    },
    historia: "É a região de nascimento de estrelas de grande massa mais próxima da Terra. Em 1880, Henry Draper fez dela a primeira fotografia de uma nebulosa.",
    curiosidades: [
      "Dá para vê-la a olho nu: é a “estrela” do meio da espada de Órion, logo abaixo das Três Marias.",
      "No coração dela fica o Trapézio, quatro estrelas jovens e brilhantes que acendem toda a nuvem.",
      "O Hubble encontrou ali discos de poeira ao redor de estrelas recém-nascidas, de onde podem surgir planetas.",
    ],
  },
  m45: {
    tipo: "Aglomerado aberto (Plêiades)",
    constelacao: "Touro (Taurus)",
    distancia: "cerca de 440 anos-luz",
    descoberta: {
      quem: "Conhecidas desde a Antiguidade",
      quando: "pré-história",
      como: "Aparecem em textos de Homero e Hesíodo e no disco celeste de Nebra, com mais de 3.500 anos. Galileu, em 1610, viu dezenas de estrelas a mais com sua luneta.",
    },
    historia: "Muitos povos usaram as Plêiades como calendário, marcando plantio e colheita pelo seu nascer no céu. No Brasil, são chamadas de Sete-Estrelo.",
    curiosidades: [
      "O logotipo da Subaru mostra as Plêiades: “Subaru” é o nome japonês do aglomerado.",
      "O brilho azulado em volta é luz das estrelas refletida por uma nuvem de poeira que o aglomerado está atravessando, e não sobra do seu nascimento.",
      "São estrelas jovens, com cerca de 100 milhões de anos, contra 4,6 bilhões do Sol.",
    ],
  },
  m51: {
    tipo: "Galáxia espiral em interação (Galáxia do Redemoinho)",
    constelacao: "Cães de Caça (Canes Venatici)",
    distancia: "cerca de 30 milhões de anos-luz",
    descoberta: {
      quem: "Charles Messier",
      quando: "1773",
      como: "Messier viu a galáxia principal; a pequena companheira, NGC 5195, foi achada por Pierre Méchain em 1781.",
    },
    historia: "Em 1845, Lord Rosse desenhou seus braços espirais com o maior telescópio da época. Foi a primeira “nebulosa” em que se reconheceu a forma de espiral, muito antes de se saber que era outra galáxia.",
    curiosidades: [
      "A companheira menor está passando por trás dela, e a gravidade do encontro agita o gás e acende novas estrelas.",
      "Várias supernovas foram vistas nela nas últimas décadas, como em 1994, 2005 e 2011.",
      "Vemos a galáxia quase de frente, por isso o desenho de redemoinho fica tão claro.",
    ],
  },
  m57: {
    tipo: "Nebulosa planetária (Nebulosa do Anel)",
    constelacao: "Lira (Lyra)",
    distancia: "cerca de 2.500 anos-luz",
    descoberta: {
      quem: "Antoine Darquier de Pellepoix",
      quando: "1779",
      como: "Ele a encontrou em janeiro de 1779, e Messier a registrou no mesmo mês.",
    },
    historia: "É a casca de gás de uma estrela que morreu. No centro sobrou uma anã branca, o núcleo exposto da estrela.",
    curiosidades: [
      "Não é bem um anel: tem forma de barril ou rosca, que vemos olhando de uma ponta.",
      "Em 2023, o James Webb mostrou milhares de pequenos aglomerados densos de gás na borda do anel.",
      "Fica perto de Vega, uma das estrelas mais brilhantes do céu, o que ajuda a achá-la.",
    ],
  },
  m104: {
    tipo: "Galáxia (Galáxia do Sombreiro)",
    constelacao: "Virgem (Virgo)",
    distancia: "cerca de 30 milhões de anos-luz",
    descoberta: {
      quem: "Pierre Méchain",
      quando: "1781",
      como: "Messier anotou à mão a descoberta do colega; ela só entrou oficialmente no catálogo em 1921, quando a anotação foi encontrada.",
    },
    historia: "Em 1912, Vesto Slipher mediu que ela se afasta de nós a cerca de 1.000 km por segundo. Foi uma das primeiras pistas de que as galáxias estão se afastando, e de que o Universo está em expansão.",
    curiosidades: [
      "Vista quase de lado, a faixa escura de poeira e o núcleo brilhante lembram um chapéu mexicano.",
      "No centro há um buraco negro com cerca de um bilhão de vezes a massa do Sol.",
      "Em infravermelho, a faixa de poeira brilha e aparece como um anel ao redor da galáxia.",
    ],
  },
  ngc3372: {
    tipo: "Nebulosa de formação estelar (Nebulosa da Carina)",
    constelacao: "Quilha (Carina)",
    distancia: "cerca de 7.500 anos-luz",
    descoberta: {
      quem: "Nicolas-Louis de Lacaille",
      quando: "1751–1752",
      como: "Catalogada durante sua expedição ao Cabo da Boa Esperança, para mapear o céu do hemisfério sul.",
    },
    historia: "Abriga Eta Carinae, uma estrela gigantesca e instável. Em 1843, uma erupção a tornou a segunda estrela mais brilhante do céu por alguns anos. Um dia ela deve explodir como supernova.",
    curiosidades: [
      "É maior e mais brilhante que a Nebulosa de Órion, mas fica no céu do sul: do Brasil, a vista é ótima.",
      "Os “Penhascos Cósmicos”, uma das primeiras imagens do James Webb em 2022, ficam no complexo da Carina.",
      "Tem algumas das estrelas de maior massa conhecidas na nossa galáxia.",
    ],
  },
  sgra: {
    tipo: "Buraco negro supermassivo no centro da Via Láctea",
    constelacao: "Sagitário (Sagittarius)",
    distancia: "cerca de 26.000 anos-luz",
    descoberta: {
      quem: "Bruce Balick e Robert Brown",
      quando: "1974",
      como: "Detectado como uma fonte de rádio compacta e muito intensa no centro da galáxia.",
    },
    historia: "Durante décadas, equipes acompanharam estrelas girando em volta de um ponto invisível. Esse trabalho rendeu o Nobel de Física de 2020 a Reinhard Genzel e Andrea Ghez. Em 2022, o Event Horizon Telescope divulgou a primeira imagem da sombra desse buraco negro.",
    curiosidades: [
      "Tem cerca de 4 milhões de vezes a massa do Sol.",
      "A estrela S2 dá uma volta completa ao redor dele a cada 16 anos.",
      "A poeira bloqueia a luz visível vinda do centro da galáxia; por isso se observa essa região em infravermelho, como o SPHEREx faz, e em rádio.",
    ],
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
    curiosidades: ["It has the largest known proper motion of any star: it crosses a full Moon's width of sky about every 180 years."],
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
    curiosidades: ["Its temperature is close to 0 °C (32 °F), like a winter day here on Earth. For a “star”, that is freezing."],
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
    curiosidades: ["For a decade it was the closest known pair of brown dwarfs. Because they orbit each other, their masses can be measured, which is rare for this kind of object."],
    oQueVer: "Motion: the source shifts slightly left and down between epochs.",
  },
  "rw-aur": {
    tipo: "Young star (T Tauri type), in a binary system",
    constelacao: "Auriga",
    distancia: "about 500 light-years",
    historia: "It is only a few million years old, a baby on stellar scales, and is still surrounded by the disk of gas and dust where planets can form. Since 2010 it has gone through deep dimming events, probably caused by dust from that disk passing in front of the star.",
    curiosidades: ["Studying it helps us understand what the Sun was like right after it was born."],
    oQueVer: "Brightness: compare how bright it appears in each epoch.",
  },
  "r-dra": {
    tipo: "Variable red giant (Mira type)",
    constelacao: "Draco",
    historia: "Mira-type stars are near the end of their lives: they swell and shrink in regular cycles, changing brightness a lot. R Draconis completes a cycle in about 8 months.",
    curiosidades: ["At its brightest it can be seen with binoculars; at its faintest it is hundreds of times dimmer."],
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
    curiosidades: [
      "The light you are seeing left it before there were humans on Earth.",
      "It is about 170,000 light-years across, almost twice the size of the Milky Way.",
      "Supernova SN 2011fe was one of the closest of its kind in decades and could be seen with binoculars.",
    ],
    oQueVer: "Context: galaxies do not visibly move in a few years; differences between epochs are usually stars from our own galaxy in the foreground.",
  },
  m1: {
    tipo: "Supernova remnant (Crab Nebula)",
    constelacao: "Taurus",
    distancia: "about 6,500 light-years",
    descoberta: {
      quem: "John Bevis; later Charles Messier",
      quando: "1731 · 1758",
      como: "Messier found it while searching for the return of Halley's comet. To avoid mistaking fixed clouds for comets again, he started his famous catalog, and it became number 1.",
    },
    historia: "It is what remains of a star that exploded and was seen from Earth in 1054. Chinese astronomers recorded a “guest star” so bright it was visible in daylight for 23 days.",
    curiosidades: [
      "The name “Crab” comes from an 1844 drawing by astronomer Lord Rosse, who thought it looked like one.",
      "A pulsar spins at its center: a neutron star about 20 km across that turns roughly 30 times per second.",
      "The cloud is still expanding at about 1,500 km per second.",
    ],
  },
  m8: {
    tipo: "Star-forming nebula (Lagoon Nebula)",
    constelacao: "Sagittarius",
    distancia: "about 4,000 light-years",
    descoberta: {
      quem: "Giovanni Battista Hodierna",
      quando: "before 1654",
      como: "Recorded as a nebulous patch through a telescope; Messier added it to his catalog in 1764.",
    },
    historia: "It is a stellar nursery: hydrogen gas lit up by the radiation of young, hot stars. The dark “lagoon” that gives it its name is a lane of dust crossing the cloud.",
    curiosidades: [
      "Under dark skies you can see it with the naked eye, as a small smudge above the “teapot” of Sagittarius.",
      "In the sky it covers a larger area than the full Moon.",
      "It has small, dense dark clouds called Bok globules, where new stars may be forming right now.",
    ],
  },
  m16: {
    tipo: "Nebula with a star cluster (Eagle Nebula)",
    constelacao: "Serpens",
    distancia: "about 7,000 light-years",
    descoberta: {
      quem: "Philippe Loys de Chéseaux",
      quando: "1745–1746",
      como: "He saw the star cluster; Messier, in 1764, noticed the surrounding nebulosity.",
    },
    historia: "It became famous in 1995 with the Hubble image called the “Pillars of Creation”: columns of gas and dust where stars are being born. In 2022, James Webb retook the picture in infrared.",
    curiosidades: [
      "Each pillar is a few light-years tall: the Solar System would fit inside thousands of times.",
      "In infrared, like SPHEREx's, dust becomes more transparent and stars hidden inside the pillars show up.",
      "Radiation from nearby young stars is slowly “evaporating” the pillars.",
    ],
  },
  m27: {
    tipo: "Planetary nebula (Dumbbell Nebula)",
    constelacao: "Vulpecula",
    distancia: "about 1,360 light-years",
    descoberta: {
      quem: "Charles Messier",
      quando: "1764",
      como: "It was the first planetary nebula ever discovered.",
    },
    historia: "It is gas thrown off by a Sun-like star at the end of its life. The leftover core, a very hot white dwarf, makes that gas glow.",
    curiosidades: [
      "“Planetary nebula” has nothing to do with planets: William Herschel coined the name because through a telescope they looked like planet disks.",
      "In about 5 billion years, the Sun should form a similar nebula.",
      "It is named after its resemblance to a dumbbell.",
    ],
  },
  m31: {
    tipo: "Spiral galaxy (Andromeda Galaxy)",
    constelacao: "Andromeda",
    distancia: "about 2.5 million light-years",
    descoberta: {
      quem: "Abd al-Rahman al-Sufi",
      quando: "964",
      como: "The Persian astronomer described it as a “small cloud” in his Book of Fixed Stars, centuries before the telescope.",
    },
    historia: "Until the 1920s many thought it was a cloud inside the Milky Way. In 1923, Edwin Hubble found a variable star in it that allowed its distance to be measured, proving it was another galaxy. The Universe got much bigger overnight.",
    curiosidades: [
      "It is one of the most distant things you can see with the naked eye.",
      "In the sky it spans about 3°, roughly six full Moons side by side. We just don't see all of it because its edges are faint.",
      "It and the Milky Way are approaching each other and may merge in a few billion years.",
    ],
  },
  m42: {
    tipo: "Star-forming nebula (Orion Nebula)",
    constelacao: "Orion",
    distancia: "about 1,350 light-years",
    descoberta: {
      quem: "Nicolas-Claude Fabri de Peiresc",
      quando: "1610",
      como: "It is the first known telescopic record of it. To the naked eye it was already seen as a fuzzy “star”.",
    },
    historia: "It is the closest region to Earth where massive stars are being born. In 1880, Henry Draper made it the subject of the first photograph of a nebula.",
    curiosidades: [
      "You can see it with the naked eye: it is the middle “star” of Orion's sword, just below the belt.",
      "At its heart lies the Trapezium, four young, bright stars that light up the whole cloud.",
      "Hubble found disks of dust around newborn stars there, where planets may form.",
    ],
  },
  m45: {
    tipo: "Open cluster (Pleiades)",
    constelacao: "Taurus",
    distancia: "about 440 light-years",
    descoberta: {
      quem: "Known since antiquity",
      quando: "prehistory",
      como: "They appear in the writings of Homer and Hesiod and on the Nebra sky disk, more than 3,500 years old. In 1610, Galileo saw dozens of extra stars with his telescope.",
    },
    historia: "Many cultures used the Pleiades as a calendar, timing planting and harvest by their rising in the sky. In Brazil they are called Sete-Estrelo (“Seven Stars”).",
    curiosidades: [
      "The Subaru logo shows the Pleiades: “Subaru” is the cluster's Japanese name.",
      "The bluish glow around them is starlight reflected by a dust cloud the cluster is passing through, not leftovers from its birth.",
      "They are young stars, about 100 million years old, compared with the Sun's 4.6 billion.",
    ],
  },
  m51: {
    tipo: "Interacting spiral galaxy (Whirlpool Galaxy)",
    constelacao: "Canes Venatici",
    distancia: "about 30 million light-years",
    descoberta: {
      quem: "Charles Messier",
      quando: "1773",
      como: "Messier saw the main galaxy; its small companion, NGC 5195, was found by Pierre Méchain in 1781.",
    },
    historia: "In 1845, Lord Rosse sketched its spiral arms with the largest telescope of the time. It was the first “nebula” recognized as a spiral, long before anyone knew it was another galaxy.",
    curiosidades: [
      "The smaller companion is passing behind it, and the gravity of the encounter stirs up gas and sparks new stars.",
      "Several supernovae have been seen in it in recent decades, for example in 1994, 2005 and 2011.",
      "We see it almost face-on, which is why the whirlpool pattern is so clear.",
    ],
  },
  m57: {
    tipo: "Planetary nebula (Ring Nebula)",
    constelacao: "Lyra",
    distancia: "about 2,500 light-years",
    descoberta: {
      quem: "Antoine Darquier de Pellepoix",
      quando: "1779",
      como: "He found it in January 1779, and Messier recorded it the same month.",
    },
    historia: "It is the gas shell of a star that died. A white dwarf, the star's exposed core, remains at the center.",
    curiosidades: [
      "It isn't really a ring: it is shaped like a barrel or doughnut that we see end-on.",
      "In 2023, James Webb revealed thousands of small, dense clumps of gas along the edge of the ring.",
      "It sits near Vega, one of the brightest stars in the sky, which helps you find it.",
    ],
  },
  m104: {
    tipo: "Galaxy (Sombrero Galaxy)",
    constelacao: "Virgo",
    distancia: "about 30 million light-years",
    descoberta: {
      quem: "Pierre Méchain",
      quando: "1781",
      como: "Messier noted his colleague's discovery by hand; it only officially joined the catalog in 1921, when that note was found.",
    },
    historia: "In 1912, Vesto Slipher measured it moving away from us at about 1,000 km per second. It was one of the first clues that galaxies are receding, and that the Universe is expanding.",
    curiosidades: [
      "Seen almost edge-on, its dark dust lane and bright core look like a Mexican sombrero.",
      "At its center is a black hole about a billion times the mass of the Sun.",
      "In infrared, the dust lane glows and shows up as a ring around the galaxy.",
    ],
  },
  ngc3372: {
    tipo: "Star-forming nebula (Carina Nebula)",
    constelacao: "Carina",
    distancia: "about 7,500 light-years",
    descoberta: {
      quem: "Nicolas-Louis de Lacaille",
      quando: "1751–1752",
      como: "Cataloged during his expedition to the Cape of Good Hope to map the southern sky.",
    },
    historia: "It hosts Eta Carinae, a huge and unstable star. In 1843 an eruption made it the second-brightest star in the sky for a few years. One day it is expected to explode as a supernova.",
    curiosidades: [
      "It is larger and brighter than the Orion Nebula, but it lies in the southern sky: from Brazil the view is great.",
      "The “Cosmic Cliffs”, one of James Webb's first images in 2022, are part of the Carina complex.",
      "It contains some of the most massive stars known in our galaxy.",
    ],
  },
  sgra: {
    tipo: "Supermassive black hole at the center of the Milky Way",
    constelacao: "Sagittarius",
    distancia: "about 26,000 light-years",
    descoberta: {
      quem: "Bruce Balick and Robert Brown",
      quando: "1974",
      como: "Detected as a compact, very intense radio source at the center of the galaxy.",
    },
    historia: "For decades, teams tracked stars orbiting an invisible point. That work earned Reinhard Genzel and Andrea Ghez the 2020 Nobel Prize in Physics. In 2022, the Event Horizon Telescope released the first image of this black hole's shadow.",
    curiosidades: [
      "It has about 4 million times the mass of the Sun.",
      "The star S2 completes an orbit around it every 16 years.",
      "Dust blocks visible light from the galactic center, so this region is observed in infrared, as SPHEREx does, and in radio.",
    ],
  },
};

export const targetInfo: Record<Locale, Record<string, TargetInfo>> = { pt, en };

const galaxy = { pt: "Galáxia", en: "Galaxy" };
const nebula = { pt: "Nebulosa", en: "Nebula" };
const planetary = { pt: "Nebulosa planetária", en: "Planetary nebula" };

// Identificações e notas de observação do catálogo de presets SPHEREye.
export const presetFacts: Partial<Record<string, {
  catalog: string;
  kind: Record<Locale, string>;
  note?: Record<Locale, string>;
}>> = {
  "preset-m1": {
    catalog: "M1 / NGC 1952",
    kind: { pt: "Remanescente de supernova", en: "Supernova remnant" },
    note: { pt: "Ocupa cerca de 7′ no céu.", en: "It spans about 7′ in the sky." },
  },
  "preset-m8": { catalog: "M8 / NGC 6523", kind: nebula },
  "preset-m16": { catalog: "M16 / NGC 6611", kind: nebula },
  "preset-m27": {
    catalog: "M27 / NGC 6853",
    kind: planetary,
    note: { pt: "Ocupa cerca de 8′ no céu.", en: "It spans about 8′ in the sky." },
  },
  "preset-m31": {
    catalog: "M31 / NGC 224",
    kind: galaxy,
    note: { pt: "A galáxia ocupa cerca de 3° no céu e tem um núcleo muito brilhante.", en: "The galaxy spans about 3° in the sky and has a very bright core." },
  },
  "preset-m42": {
    catalog: "M42 / NGC 1976",
    kind: nebula,
    note: { pt: "O núcleo brilhante pode saturar e aparecer como uma lacuna no recorte.", en: "The bright core can saturate and appear as a gap in the cutout." },
  },
  "preset-m45": {
    catalog: "M45",
    kind: { pt: "Aglomerado aberto", en: "Open cluster" },
    note: { pt: "O aglomerado ocupa cerca de 2° no céu, e estrelas brilhantes dominam o recorte.", en: "The cluster spans about 2° in the sky, and bright stars dominate the cutout." },
  },
  "preset-m51": { catalog: "M51 / NGC 5194", kind: galaxy },
  "preset-m57": {
    catalog: "M57 / NGC 6720",
    kind: planetary,
    note: { pt: "A nebulosa mede cerca de 1′ e ocupa poucos pixels no recorte.", en: "The nebula spans about 1′ and covers only a few pixels in the cutout." },
  },
  "preset-m101": { catalog: "M101 / NGC 5457", kind: galaxy },
  "preset-m104": { catalog: "M104 / NGC 4594", kind: galaxy },
  "preset-ngc3372": { catalog: "NGC 3372", kind: nebula },
  "preset-sgra": {
    catalog: "Sgr A*",
    kind: { pt: "Centro galáctico", en: "Galactic center" },
    note: { pt: "O campo é muito denso e brilhante.", en: "The field is very dense and bright." },
  },
};
