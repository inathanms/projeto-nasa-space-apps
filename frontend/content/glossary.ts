import type { Locale } from "../lib/i18n";

// Explicações curtas para iniciantes. Uma ou duas frases, sem jargão novo.
const pt = {
  "ascensao-reta": "É a \"longitude\" do céu: diz a posição de um astro na direção leste–oeste, de 0° a 360°.",
  declinacao: "É a \"latitude\" do céu: diz quão ao norte (+90°) ou ao sul (−90°) do equador celeste um astro está.",
  icrs: "Sistema de referência padrão usado por astrônomos para que todos usem as mesmas coordenadas para o mesmo ponto do céu.",
  epoca: "O momento em que uma foto do céu foi tirada. Comparar épocas diferentes revela o que se moveu ou mudou de brilho.",
  irsa: "Arquivo público da NASA (Caltech/IPAC) que guarda as imagens infravermelhas de missões como a SPHEREx.",
  "comprimento-de-onda": "A \"cor\" da luz. A SPHEREx enxerga infravermelho, invisível ao olho humano, medido em micrômetros (µm).",
  fits: "Formato de arquivo usado na astronomia para guardar imagens junto com dados sobre a observação.",
  "orbita-polar": "Órbita que passa sobre os polos da Terra. Enquanto a Terra gira por baixo, o satélite consegue observar o céu inteiro.",
};

export type GlossaryKey = keyof typeof pt;

const en: Record<GlossaryKey, string> = {
  "ascensao-reta": "The sky's \"longitude\": it gives an object's east–west position, from 0° to 360°.",
  declinacao: "The sky's \"latitude\": how far north (+90°) or south (−90°) of the celestial equator an object is.",
  icrs: "The standard reference system astronomers use so everyone gives the same coordinates for the same point in the sky.",
  epoca: "The moment a picture of the sky was taken. Comparing different epochs reveals what moved or changed brightness.",
  irsa: "NASA's public archive (Caltech/IPAC) that stores infrared images from missions such as SPHEREx.",
  "comprimento-de-onda": "The \"color\" of light. SPHEREx sees infrared, invisible to the human eye, measured in micrometers (µm).",
  fits: "A file format used in astronomy to store images together with data about the observation.",
  "orbita-polar": "An orbit that passes over Earth's poles. As Earth turns underneath, the satellite can observe the whole sky.",
};

export const glossary: Record<Locale, Record<GlossaryKey, string>> = { pt, en };
