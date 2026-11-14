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
