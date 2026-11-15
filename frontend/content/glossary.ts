// Explicações curtas para iniciantes. Uma ou duas frases, sem jargão novo.
export const glossary = {
  "ascensao-reta": "É a \"longitude\" do céu: diz a posição de um astro na direção leste–oeste, de 0° a 360°.",
  declinacao: "É a \"latitude\" do céu: diz quão ao norte (+90°) ou ao sul (−90°) do equador celeste um astro está.",
  icrs: "Sistema de referência padrão usado por astrônomos para que todos usem as mesmas coordenadas para o mesmo ponto do céu.",
  epoca: "O momento em que uma foto do céu foi tirada. Comparar épocas diferentes revela o que se moveu ou mudou de brilho.",
  irsa: "Arquivo público da NASA (Caltech/IPAC) que guarda as imagens infravermelhas de missões como a SPHEREx.",
  "comprimento-de-onda": "A \"cor\" da luz. A SPHEREx enxerga infravermelho, invisível ao olho humano, medido em micrômetros (µm).",
  fits: "Formato de arquivo usado na astronomia para guardar imagens junto com dados sobre a observação.",
  "orbita-polar": "Órbita que passa sobre os polos da Terra. Enquanto a Terra gira por baixo, o satélite consegue observar o céu inteiro.",
} as const;

export type GlossaryKey = keyof typeof glossary;
