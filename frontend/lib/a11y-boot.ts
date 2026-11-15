// Constantes de acessibilidade sem dependência de React, para poderem ser usadas no layout
// (Server Component). A lógica com hooks fica em lib/a11y.ts.

export type A11ySettings = {
  text: "md" | "lg" | "xl";
  colorblind: boolean;
  contrast: boolean;
  motion: boolean;
  underline: boolean;
  readable: boolean;
  libras: boolean;
};

export const A11Y_KEY = "spheReye:a11y:v1";
export const A11Y_DEFAULTS: A11ySettings = {
  text: "md", colorblind: false, contrast: false, motion: false, underline: false, readable: false, libras: false,
};

/**
 * Script que roda no <head> antes da pintura, para a página já abrir com as preferências
 * (sem piscar com o tamanho ou as cores padrão).
 */
export const A11Y_BOOT_SCRIPT = `(function(){try{var s=JSON.parse(localStorage.getItem(${JSON.stringify(A11Y_KEY)})||"null");if(!s)return;var d=${JSON.stringify(A11Y_DEFAULTS)};for(var k in s){if(k in d&&s[k]!==d[k])document.documentElement.setAttribute("data-a11y-"+k,String(s[k]));}}catch(e){}})();`;
