import { alvos } from "./landing";

export const exampleNames = new Map([
  ...alvos.map(({ slug, nome }) => [slug, nome] as const),
  ["m101", "Galáxia M101"],
  ["prototipo", "Campo simulado"],
]);

export const exampleAliases: Readonly<Record<string, string>> = {
  "wise-0855": "wise0855",
  "r-draconis": "r-dra",
  "rw-aurigae": "rw-aur",
};

export const exampleDescriptions: Readonly<Record<string, string>> = {
  barnard: "Os dois recortes mostram o mesmo campo da Estrela de Barnard em datas diferentes. As estrelas ao redor são a referência para investigar o deslocamento do alvo.",
  m101: "A galáxia aparece como uma região difusa mais brilhante perto do centro. Os dois recortes mostram o mesmo campo em datas diferentes.",
  wise0855: "Na simulação, o ponto alaranjado sai de pouco abaixo e à esquerda do centro para pouco acima e à direita. O brilho do ponto fica constante.",
  "rw-aur": "Na simulação, o ponto no centro permanece na mesma posição e fica maior e mais brilhante na segunda época.",
  "r-dra": "Na simulação, o ponto no centro permanece na mesma posição e fica menor e menos brilhante na segunda época.",
};
