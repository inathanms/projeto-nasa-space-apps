import type { Metadata } from "next";

export const routes = {
  explorar: {
    title: "Explorar o céu",
    description: "Percorra as observações de um campo e compare imagens de épocas diferentes.",
  },
  observatorio: {
    title: "Observatório orbital",
    description: "Ajuste a mira de uma cena orbital e registre alvos no diário de bordo.",
  },
  laboratorio: {
    title: "Laboratório de apontamento",
    description: "Gire o globo e incline a linha de visão do telescópio. Use as coordenadas resultantes para buscar um campo no explorador.",
  },
  entregas: {
    title: "Entregas",
    description: "Experimente o projeto à medida que ele avança, da primeira interface à consulta por coordenadas.",
  },
};

export function metadataFor({ title, description }: typeof routes[keyof typeof routes]): Metadata {
  return {
    title,
    description,
    openGraph: { title, description, type: "website", locale: "pt_BR", siteName: "SPHEREye" },
  };
}
