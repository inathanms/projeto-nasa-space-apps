import { getLanding } from "./landing";
import { translators, type Locale } from "../lib/i18n";

export function exampleNames(locale: Locale) {
  const { alvos } = getLanding(locale);
  const t = translators[locale];
  return new Map([
    ...alvos.map(({ slug, nome }) => [slug, nome] as const),
    ["m101", t("Galáxia M101")],
    ["prototipo", t("Campo simulado")],
    ["preset-m1", t("M1 · Nebulosa do Caranguejo")],
    ["preset-m8", t("M8 · Nebulosa da Lagoa")],
    ["preset-m16", t("M16 · Nebulosa da Águia")],
    ["preset-m27", t("M27 · Nebulosa do Haltere")],
    ["preset-m31", t("M31 · Galáxia de Andrômeda")],
    ["preset-m42", t("M42 · Nebulosa de Órion")],
    ["preset-m45", t("M45 · Plêiades")],
    ["preset-m51", t("M51 · Galáxia do Redemoinho")],
    ["preset-m57", t("M57 · Nebulosa do Anel")],
    ["preset-m101", t("M101 · Galáxia do Cata-vento")],
    ["preset-m104", t("M104 · Galáxia do Sombreiro")],
    ["preset-ngc3372", t("NGC 3372 · Nebulosa da Carina")],
    ["preset-sgra", t("Sgr A* · Centro Galáctico")],
  ]);
}

export const exampleAliases: Readonly<Record<string, string>> = {
  "wise-0855": "wise0855",
  "r-draconis": "r-dra",
  "rw-aurigae": "rw-aur",
};

export function exampleDescriptions(locale: Locale): Readonly<Record<string, string>> {
  const t = translators[locale];
  return {
    barnard: t("Os dois recortes mostram o mesmo campo da Estrela de Barnard em datas diferentes. As estrelas ao redor são a referência para investigar o deslocamento do alvo."),
    m101: t("A galáxia aparece como uma região difusa mais brilhante perto do centro. Os dois recortes mostram o mesmo campo em datas diferentes."),
    wise0855: t("Na simulação, o ponto alaranjado sai de pouco abaixo e à esquerda do centro para pouco acima e à direita. O brilho do ponto fica constante."),
    "rw-aur": t("Na simulação, o ponto no centro permanece na mesma posição e fica maior e mais brilhante na segunda época."),
    "r-dra": t("Na simulação, o ponto no centro permanece na mesma posição e fica menor e menos brilhante na segunda época."),
  };
}
