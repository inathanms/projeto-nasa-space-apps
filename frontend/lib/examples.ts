import "server-only";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import type { Locale } from "./i18n";
import { exampleNames } from "../content/examples";
import { isSequence, type Example } from "./sequence";

export function getExamples(locale: Locale): [Example, ...Example[]] {
  const names = exampleNames(locale);
  const root = join(process.cwd(), "public", "examples");
  const examples = readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map(({ name: slug }) => {
      const sequence: unknown = JSON.parse(readFileSync(join(root, slug, "manifest.json"), "utf8"));
      if (!isSequence(sequence)) throw new Error(`Manifesto incompatível: ${slug}`);
      return { slug, name: names.get(slug) ?? slug.toUpperCase(), sequence, synthetic: sequence.is_synthetic ?? slug === "prototipo" };
    })
    .sort((a, b) => Number(a.synthetic) - Number(b.synthetic) ||
      Number(b.slug === "eps-indi-b") - Number(a.slug === "eps-indi-b") || a.slug.localeCompare(b.slug));
  const [first, ...rest] = examples;
  if (!first) throw new Error("Nenhum exemplo disponível para o explorador.");
  return [first, ...rest];
}
