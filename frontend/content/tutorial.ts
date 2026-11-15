import { localizedHref, type Locale } from "../lib/i18n";

// Passos do tutorial guiado. Cada passo pode trocar de tela (`route`, escrita em português e
// traduzida para a rota do idioma) e destacar um elemento marcado com data-tour="…".
// Sem `target`, o balão aparece no centro. Textos para iniciantes: frases curtas.

export type TourStep = {
  route?: string;
  target?: string;
  title: string;
  body: string;
};

type Text = { title: string; body: string };
type Source = { route?: string; target?: string; pt: Text; en: Text };

export const TUTORIAL_KEY = "spheReye:tutorial:v1";

const steps: Source[] = [
  {
    route: "/explorar/",
    pt: {
      title: "Bem-vindo ao SPHEREye",
      body: "Em poucos passos você vai aprender a comparar fotos do céu feitas pelo telescópio SPHEREx, da NASA, e a encontrar astros que se movem ou mudam de brilho. Pode pular quando quiser.",
    },
    en: {
      title: "Welcome to SPHEREye",
      body: "In a few steps you will learn to compare sky images taken by NASA's SPHEREx telescope and find objects that move or change brightness. You can skip at any time.",
    },
  },
  {
    route: "/explorar/",
    target: "explorar-exemplos",
    pt: {
      title: "Escolha um astro",
      body: "Comece por aqui: escolha um astro de exemplo e clique em “Abrir exemplo”. Os exemplos funcionam mesmo sem conexão com a NASA.",
    },
    en: {
      title: "Pick an object",
      body: "Start here: choose an example object and click “Open example”. Examples work even without a connection to NASA.",
    },
  },
  {
    route: "/explorar/",
    target: "explorar-visor",
    pt: {
      title: "O visor",
      body: "Esta é uma foto real do céu em infravermelho. “N ↑” e “E ←” mostram onde ficam o norte e o leste, e a barrinha “1′” dá a escala (1′ é 1/60 de grau).",
    },
    en: {
      title: "The viewer",
      body: "This is a real infrared image of the sky. “N ↑” and “E ←” show where north and east are, and the “1′” bar gives the scale (1′ is 1/60 of a degree).",
    },
  },
  {
    route: "/explorar/",
    target: "explorar-epocas",
    pt: {
      title: "Compare as épocas",
      body: "Cada época é uma foto do mesmo pedaço do céu em uma data diferente. Alterne entre elas ou aperte “Reproduzir”: o que mudar de lugar ou de brilho é a sua descoberta.",
    },
    en: {
      title: "Compare the epochs",
      body: "Each epoch is an image of the same patch of sky on a different date. Switch between them or press “Play”: whatever changes position or brightness is your discovery.",
    },
  },
  {
    route: "/explorar/",
    target: "explorar-marcar",
    pt: {
      title: "Não sabe para onde olhar?",
      body: "Este botão desenha uma moldura em volta do astro. Use quando estiver difícil achá-lo no meio das estrelas.",
    },
    en: {
      title: "Not sure where to look?",
      body: "This button draws a frame around the object. Use it when it is hard to spot among the stars.",
    },
  },
  {
    route: "/explorar/",
    target: "explorar-busca",
    pt: {
      title: "Busque qualquer ponto do céu",
      body: "Digite coordenadas para buscar outras regiões no arquivo da NASA. Não conhece algum termo? Toque no “?” ao lado dele.",
    },
    en: {
      title: "Search any point in the sky",
      body: "Enter coordinates to search other regions in NASA's archive. Don't know a term? Tap the “?” next to it.",
    },
  },
  {
    route: "/explorar/",
    target: "explorar-origem",
    pt: {
      title: "De onde vêm os dados",
      body: "Aqui ficam a data exata da foto, o instrumento e o link para o arquivo original. Boa ciência sempre mostra a fonte.",
    },
    en: {
      title: "Where the data comes from",
      body: "Here you find the exact date of the image, the instrument and the link to the original file. Good science always shows its source.",
    },
  },
  {
    route: "/explorar/",
    target: "explorar-orbita",
    pt: {
      title: "Onde estava o telescópio",
      body: "Veja em 3D onde a SPHEREx estava no momento em que a foto foi tirada.",
    },
    en: {
      title: "Where the telescope was",
      body: "See in 3D where SPHEREx was at the moment the image was taken.",
    },
  },
  {
    route: "/observatorio/",
    target: "obs-alvos",
    pt: {
      title: "Observatório orbital",
      body: "Agora é você quem aponta o telescópio. Escolha um alvo para ir direto até ele, ou fique no modo “Manual” para procurar por conta própria.",
    },
    en: {
      title: "Orbital observatory",
      body: "Now you point the telescope. Choose a target to jump straight to it, or stay in “Manual” mode to search on your own.",
    },
  },
  {
    route: "/observatorio/",
    target: "obs-ra",
    pt: {
      title: "Mire na horizontal",
      body: "A ascensão reta move a mira de leste a oeste, como a longitude em um mapa.",
    },
    en: {
      title: "Aim horizontally",
      body: "Right ascension moves the aim east to west, like longitude on a map.",
    },
  },
  {
    route: "/observatorio/",
    target: "obs-dec",
    pt: {
      title: "Mire na vertical",
      body: "A declinação move a mira para o norte ou para o sul, como a latitude. Achou algo? “Importar para o explorador” leva essas coordenadas para ver as fotos reais.",
    },
    en: {
      title: "Aim vertically",
      body: "Declination moves the aim north or south, like latitude. Found something? “Import to explorer” takes these coordinates over to see the real images.",
    },
  },
  {
    route: "/observatorio/",
    target: "obs-diario",
    pt: {
      title: "Diário de bordo",
      body: "Ele avisa quando a mira está chegando perto de um alvo. Ao descobrir um, abra a ficha para ver as coordenadas e acessar as imagens.",
    },
    en: {
      title: "Logbook",
      body: "It tells you when your aim is getting close to a target. When you discover one, open its details to see the coordinates and access the images.",
    },
  },
  {
    route: "/observatorio/",
    target: "obs-tempo",
    pt: {
      title: "Controle o tempo",
      body: "Avance ou volte no tempo para ver a Terra girar na simulação.",
    },
    en: {
      title: "Control time",
      body: "Move forward or back in time to watch Earth rotate in the simulation.",
    },
  },
  {
    target: "discovery-bubble",
    pt: {
      title: "Achou algo diferente?",
      body: "Se notar algo estranho, toque aqui. O assistente te ajuda a conferir se já é conhecido e, se for novo, a montar o relatório para o Minor Planet Center.",
    },
    en: {
      title: "Found something odd?",
      body: "If you notice something strange, tap here. The assistant helps you check whether it's already known and, if it's new, build the report for the Minor Planet Center.",
    },
  },
  {
    target: "tour-help",
    pt: {
      title: "Pronto!",
      body: "Você pode rever este tutorial quando quiser por este botão. Bons céus!",
    },
    en: {
      title: "All set!",
      body: "You can replay this tutorial any time with this button. Clear skies!",
    },
  },
];

export function tutorialSteps(locale: Locale): TourStep[] {
  return steps.map(({ route, target, ...text }) => ({
    route: route ? localizedHref(locale, route) : undefined,
    target,
    ...text[locale],
  }));
}
