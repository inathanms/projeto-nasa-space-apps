import type { Locale } from "../lib/i18n";

type TargetCopy = { description: string; comparison: string; fact: string };
type TargetBrief = {
  source: { name: string; href: string };
} & Record<Locale, TargetCopy>;

const messier = (number: number) => ({
  name: "NASA · Hubble",
  href: `https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-messier-catalog/messier-${number}/`,
});

export const offlineTargetBriefs: Partial<Record<string, TargetBrief>> = {
  "preset-m1": {
    source: messier(1),
    en: {
      description: "The Crab Nebula is the expanding debris of a supernova, with a rapidly spinning neutron star at its center.",
      comparison: "Locate the bright, elongated nebula in both cutouts. Use nearby stars as landmarks and see how each rendering separates the nebula from the background.",
      fact: "Astronomers in China recorded the supernova in 1054. It was bright enough to see in daylight for nearly a month.",
    },
    pt: {
      description: "A Nebulosa do Caranguejo é o material em expansão de uma supernova, com uma estrela de nêutrons que gira rapidamente no centro.",
      comparison: "Localize a nebulosa brilhante e alongada nos dois recortes. Use as estrelas vizinhas como referência e veja como cada formato distingue a nebulosa do fundo.",
      fact: "Astrônomos chineses registraram a supernova em 1054. Ela pôde ser vista à luz do dia por quase um mês.",
    },
  },
  "preset-m8": {
    source: messier(8),
    en: {
      description: "The Lagoon Nebula is a cloud of gas and dust in Sagittarius where young stars ionize the surrounding gas.",
      comparison: "Trace one dark band against the diffuse emission, then locate it again using the same nearby stars. Compare the shape of the band instead of the brightness of a single pixel.",
      fact: "The Lagoon has its own young open cluster, NGC 6530.",
    },
    pt: {
      description: "A Nebulosa da Lagoa é uma nuvem de gás e poeira em Sagitário onde estrelas jovens ionizam o gás ao redor.",
      comparison: "Siga uma faixa escura sobre a emissão difusa e reencontre-a pelas mesmas estrelas próximas. Compare o formato da faixa em vez do brilho de um único pixel.",
      fact: "A Lagoa abriga seu próprio aglomerado aberto jovem, o NGC 6530.",
    },
  },
  "preset-m16": {
    source: messier(16),
    en: {
      description: "Messier 16 combines the Eagle emission nebula, IC 4703, with the young open cluster NGC 6611.",
      comparison: "The coverage changes substantially between these two cutouts. Find stars in the area visible in both images before comparing the glow of the cloud. A region outside one footprint cannot be checked for change.",
      fact: "When Hubble viewed the Pillars of Creation in infrared, it revealed stars hidden behind dust at visible wavelengths.",
    },
    pt: {
      description: "Messier 16 reúne a nebulosa de emissão da Águia, IC 4703, e o aglomerado aberto jovem NGC 6611.",
      comparison: "A cobertura muda bastante entre os dois recortes. Busque estrelas na área visível em ambas as imagens antes de comparar o brilho da nuvem. Uma região fora da área observada em uma das épocas não pode ser avaliada.",
      fact: "Ao observar os Pilares da Criação em infravermelho, o Hubble revelou estrelas que a poeira escondia em luz visível.",
    },
  },
  "preset-m27": {
    source: messier(27),
    en: {
      description: "The Dumbbell Nebula is a planetary nebula made from the glowing outer layers shed by an aging star.",
      comparison: "Use the star pattern near the center to locate the diffuse nebula in both cutouts. Check the faint extension on either side only where both images have data.",
      fact: "M27 was the first planetary nebula discovered. Charles Messier recorded it in 1764.",
    },
    pt: {
      description: "A Nebulosa do Haltere é uma nebulosa planetária formada pelas camadas externas luminosas expelidas por uma estrela envelhecida.",
      comparison: "Use o padrão de estrelas perto do centro para localizar a nebulosa difusa nos dois recortes. Confira suas extensões mais tênues apenas nas regiões observadas nas duas épocas.",
      fact: "M27 foi a primeira nebulosa planetária descoberta. Charles Messier a registrou em 1764.",
    },
  },
  "preset-m31": {
    source: messier(31),
    en: {
      description: "Andromeda is a neighboring spiral galaxy. Its inclined disk appears as a broad, diagonal band around a bright core.",
      comparison: "Follow the disk and match nearby foreground stars. If the cutout removes one end of the disk, compare the section visible in both images.",
      fact: "A full Hubble mosaic of Andromeda required observations from more than a thousand telescope orbits.",
    },
    pt: {
      description: "Andrômeda é uma galáxia espiral vizinha. Seu disco inclinado aparece como uma faixa diagonal larga ao redor do núcleo brilhante.",
      comparison: "Siga o disco e encontre as mesmas estrelas em primeiro plano. Se o recorte cortar uma das extremidades, compare o trecho visível nas duas imagens.",
      fact: "Um mosaico completo de Andrômeda feito pelo Hubble exigiu observações de mais de mil órbitas do telescópio.",
    },
  },
  "preset-m42": {
    source: messier(42),
    en: {
      description: "The Orion Nebula is a nearby stellar nursery below Orion’s Belt. A young cluster called the Trapezium lies in its bright central region.",
      comparison: "Compare the glow around the core in the overlap between the two cutouts. Missing data or saturation near the bright center can leave gaps. Use nearby stars to check that you are looking at the same area.",
      fact: "Hubble imaged disks of gas and dust around young stars in Orion. Structures like these can become planetary systems.",
    },
    pt: {
      description: "A Nebulosa de Órion é um berçário estelar próximo, abaixo do Cinturão de Órion. O aglomerado jovem do Trapézio fica em sua região central brilhante.",
      comparison: "Compare a emissão ao redor do núcleo na área comum aos dois recortes. Falta de dados ou saturação perto do centro brilhante pode deixar lacunas. Use estrelas próximas para confirmar que está olhando a mesma região.",
      fact: "O Hubble fotografou discos de gás e poeira em torno de estrelas jovens em Órion. Estruturas assim podem dar origem a sistemas planetários.",
    },
  },
  "preset-m45": {
    source: messier(45),
    en: {
      description: "The Pleiades, or Seven Sisters, are an open cluster in Taurus. A handful of bright members dominate the view.",
      comparison: "Match the pattern of bright stars in the strip shared by the two renderings. The RGB image covers a smaller part of this field, so use the overlap to compare star positions and structure.",
      fact: "The name Seven Sisters describes the brightest group. The cluster contains more than a thousand stars.",
    },
    pt: {
      description: "As Plêiades, ou Sete Irmãs, são um aglomerado aberto em Touro. Algumas estrelas muito brilhantes dominam a imagem.",
      comparison: "Encontre o mesmo padrão de estrelas brilhantes na faixa compartilhada pelos dois formatos. A imagem RGB cobre uma parte menor do campo, então compare as posições e a estrutura na área em comum.",
      fact: "O nome Sete Irmãs se refere ao grupo mais brilhante. O aglomerado contém mais de mil estrelas.",
    },
  },
  "preset-m51": {
    source: messier(51),
    en: {
      description: "The Whirlpool Galaxy is a face-on spiral. Its smaller companion, NGC 5195, appears next to the main galaxy.",
      comparison: "Use the two bright centers as landmarks. Check whether the faint glow around the larger galaxy keeps the same shape before interpreting any brightness differences.",
      fact: "The smaller galaxy may help shape the Whirlpool’s conspicuous spiral arms, where many new stars form.",
    },
    pt: {
      description: "A Galáxia do Redemoinho é uma espiral vista de frente. Sua companheira menor, NGC 5195, aparece junto à galáxia principal.",
      comparison: "Use os dois núcleos brilhantes como referência. Confira se a emissão mais tênue ao redor da galáxia maior mantém o formato antes de interpretar diferenças de brilho.",
      fact: "A galáxia menor pode ajudar a moldar os braços espirais do Redemoinho, onde muitas estrelas se formam.",
    },
  },
  "preset-m57": {
    source: messier(57),
    en: {
      description: "The Ring Nebula in Lyra is the glowing material shed by a Sun-like star late in its life.",
      comparison: "Find the small ring near the field center, then register the two views against neighboring stars. The ring occupies few pixels, so small changes in its outline are difficult to interpret.",
      fact: "The ring is a projection of a more complex structure. Hubble found a long lobe seen nearly end-on through the middle.",
    },
    pt: {
      description: "A Nebulosa do Anel, na constelação da Lira, é o material luminoso expelido por uma estrela parecida com o Sol no fim de sua vida.",
      comparison: "Encontre o pequeno anel perto do centro e alinhe mentalmente as imagens pelas estrelas vizinhas. O anel ocupa poucos pixels, o que dificulta interpretar pequenas mudanças no contorno.",
      fact: "O anel é a projeção de uma estrutura mais complexa. O Hubble identificou um lóbulo alongado visto quase de ponta pelo centro.",
    },
  },
  "preset-m101": {
    source: messier(101),
    en: {
      description: "The Pinwheel Galaxy is a face-on spiral in Ursa Major, with star-forming regions sprinkled along its arms.",
      comparison: "Match the compact core and the surrounding star pattern. Compare the diffuse light on the same side of the galaxy in both images, staying clear of the diagonal coverage edge.",
      fact: "One Hubble mosaic of M101 combined 51 exposures collected over nearly ten years.",
    },
    pt: {
      description: "A Galáxia do Cata-vento é uma espiral vista de frente na Ursa Maior, com regiões de formação estelar espalhadas pelos braços.",
      comparison: "Identifique o núcleo compacto e as mesmas estrelas ao redor. Compare a emissão difusa do mesmo lado da galáxia nas duas imagens, longe da borda diagonal de cobertura.",
      fact: "Um mosaico de M101 feito pelo Hubble combinou 51 exposições coletadas ao longo de quase dez anos.",
    },
  },
  "preset-m104": {
    source: messier(104),
    en: {
      description: "The Sombrero Galaxy is seen almost edge-on. A broad central bulge and a dark dust lane define its familiar silhouette.",
      comparison: "Use the slim, bright shape at the center to check the galaxy’s orientation in both epochs. Compare it with nearby unresolved stars before reading fine detail into the dust lane.",
      fact: "Astronomers estimate that the Sombrero hosts nearly 2,000 globular clusters.",
    },
    pt: {
      description: "A Galáxia do Sombreiro é vista quase de perfil. Um bojo central largo e uma faixa escura de poeira definem sua silhueta.",
      comparison: "Use a forma estreita e brilhante no centro para conferir a orientação nas duas épocas. Compare-a com estrelas próximas antes de interpretar detalhes finos na faixa de poeira.",
      fact: "Astrônomos estimam que o Sombreiro abriga cerca de 2 mil aglomerados globulares.",
    },
  },
  "preset-ngc3372": {
    source: { name: "NASA · Hubble", href: "https://science.nasa.gov/missions/hubble/dark-clouds-of-the-carina-nebula/" },
    en: {
      description: "The Carina Nebula is a large star-forming region with dense dust clouds and massive stars, including the Eta Carinae system.",
      comparison: "Start with the bright group near the middle and match the smaller stars around it. Trace a patch of diffuse emission that stays inside the shared coverage.",
      fact: "Eta Carinae became one of the brightest stars in the night sky in the nineteenth century and later faded dramatically.",
    },
    pt: {
      description: "A Nebulosa da Carina é uma grande região de formação estelar com nuvens densas de poeira e estrelas massivas, incluindo o sistema Eta Carinae.",
      comparison: "Comece pelo grupo brilhante perto do centro e encontre as mesmas estrelas menores ao redor. Siga uma região de emissão difusa dentro da área coberta pelas duas épocas.",
      fact: "Eta Carinae chegou a ser uma das estrelas mais brilhantes do céu noturno no século XIX e depois perdeu muito brilho.",
    },
  },
  "preset-sgra": {
    source: { name: "Event Horizon Telescope", href: "https://eventhorizontelescope.org/blog/astronomers-reveal-first-image-black-hole-heart-our-galaxy" },
    en: {
      description: "This infrared field covers the center of the Milky Way, where the supermassive black hole Sagittarius A* resides. The SPHEREx cutout shows the surrounding field at a much larger scale.",
      comparison: "Match several stars in the crowded field before inspecting any change near the center. In a dense region, blended sources make a bright pixel a poor way to identify a single object.",
      fact: "The Event Horizon Telescope released the first image of Sagittarius A* in 2022 using radio observations.",
    },
    pt: {
      description: "Este campo infravermelho cobre o centro da Via Láctea, onde fica o buraco negro supermassivo Sagitário A*. O recorte do SPHEREx mostra a região ao redor em uma escala muito maior.",
      comparison: "Encontre várias estrelas em comum antes de investigar mudanças perto do centro. Num campo tão denso, fontes sobrepostas tornam um único pixel brilhante uma referência pouco confiável.",
      fact: "O Event Horizon Telescope publicou a primeira imagem de Sagitário A* em 2022 usando observações em rádio.",
    },
  },
};
