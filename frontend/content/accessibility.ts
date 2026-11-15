import type { Locale } from "../lib/i18n";

const pt = {
  button: "Acessibilidade",
  title: "Acessibilidade",
  intro: "Ajuste o site do seu jeito. As escolhas ficam salvas neste navegador.",
  close: "Fechar acessibilidade",
  reset: "Restaurar padrão",
  on: "Ligado",
  off: "Desligado",

  text: "Tamanho do texto",
  textMd: "Normal",
  textLg: "Grande",
  textXl: "Muito grande",

  libras: "Libras (VLibras)",
  librasHint: "Mostra o botão do VLibras: selecione um texto e um intérprete virtual traduz para Libras.",
  colorblind: "Cores para daltonismo",
  colorblindHint: "Troca verde e laranja por azul e amarelo, fáceis de distinguir em todos os tipos comuns de daltonismo.",
  contrast: "Alto contraste",
  contrastHint: "Textos mais claros, fundos mais escuros e bordas mais fortes.",
  motion: "Reduzir movimento",
  motionHint: "Desliga animações e rolagens suaves.",
  underline: "Sublinhar links",
  underlineHint: "Mostra os links sem depender da cor.",
  readable: "Fonte de leitura fácil",
  readableHint: "Letras mais distintas e mais espaço entre linhas, útil para dislexia e baixa visão.",
};

export type AccessibilityCopy = typeof pt;

const en: AccessibilityCopy = {
  button: "Accessibility",
  title: "Accessibility",
  intro: "Adjust the site to suit you. Your choices are saved in this browser.",
  close: "Close accessibility",
  reset: "Restore defaults",
  on: "On",
  off: "Off",

  text: "Text size",
  textMd: "Normal",
  textLg: "Large",
  textXl: "Extra large",

  libras: "Libras (VLibras)",
  librasHint: "Brazilian Sign Language translation, available on the Portuguese version.",
  colorblind: "Color-blind friendly colors",
  colorblindHint: "Swaps green and orange for blue and yellow, easy to tell apart with the common types of color blindness.",
  contrast: "High contrast",
  contrastHint: "Brighter text, darker backgrounds and stronger borders.",
  motion: "Reduce motion",
  motionHint: "Turns off animations and smooth scrolling.",
  underline: "Underline links",
  underlineHint: "Shows links without relying on color.",
  readable: "Easy-reading font",
  readableHint: "More distinct letters and more line spacing, helpful for dyslexia and low vision.",
};

export const accessibilityCopy: Record<Locale, AccessibilityCopy> = { pt, en };
