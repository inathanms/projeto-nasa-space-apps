// Passos do tutorial guiado. Cada passo pode trocar de tela (`route`) e destacar um
// elemento marcado com data-tour="…". Sem `target`, o balão aparece no centro.
// Textos para iniciantes: frases curtas, sem jargão sem explicação.

export type TourStep = {
  route?: string;
  target?: string;
  title: string;
  body: string;
};

export const TUTORIAL_KEY = "spheReye:tutorial:v1";

export const tutorialSteps: TourStep[] = [
  {
    route: "/explorar/",
    title: "Bem-vindo ao SPHEREye",
    body: "Em poucos passos você vai aprender a comparar fotos do céu feitas pelo telescópio SPHEREx, da NASA, e a encontrar astros que se movem ou mudam de brilho. Pode pular quando quiser.",
  },
  {
    route: "/explorar/",
    target: "explorar-exemplos",
    title: "Escolha um astro",
    body: "Comece por aqui: escolha um astro de exemplo e clique em “Abrir exemplo”. Os exemplos funcionam mesmo sem conexão com a NASA.",
  },
  {
    route: "/explorar/",
    target: "explorar-visor",
    title: "O visor",
    body: "Esta é uma foto real do céu em infravermelho. “N ↑” e “E ←” mostram onde ficam o norte e o leste, e a barrinha “1′” dá a escala (1′ é 1/60 de grau).",
  },
  {
    route: "/explorar/",
    target: "explorar-epocas",
    title: "Compare as épocas",
    body: "Cada época é uma foto do mesmo pedaço do céu em uma data diferente. Alterne entre elas ou aperte “Reproduzir”: o que mudar de lugar ou de brilho é a sua descoberta.",
  },
  {
    route: "/explorar/",
    target: "explorar-marcar",
    title: "Não sabe para onde olhar?",
    body: "Este botão desenha uma moldura em volta do astro. Use quando estiver difícil achá-lo no meio das estrelas.",
  },
  {
    route: "/explorar/",
    target: "explorar-busca",
    title: "Busque qualquer ponto do céu",
    body: "Digite coordenadas para buscar outras regiões no arquivo da NASA. Não conhece algum termo? Toque no “?” ao lado dele.",
  },
  {
    route: "/explorar/",
    target: "explorar-origem",
    title: "De onde vêm os dados",
    body: "Aqui ficam a data exata da foto, o instrumento e o link para o arquivo original. Boa ciência sempre mostra a fonte.",
  },
  {
    route: "/explorar/",
    target: "explorar-orbita",
    title: "Onde estava o telescópio",
    body: "Veja em 3D onde a SPHEREx estava no momento em que a foto foi tirada.",
  },
  {
    route: "/observatorio/",
    target: "obs-alvos",
    title: "Observatório orbital",
    body: "Agora é você quem aponta o telescópio. Escolha um alvo para ir direto até ele, ou fique no modo “Manual” para procurar por conta própria.",
  },
  {
    route: "/observatorio/",
    target: "obs-ra",
    title: "Mire na horizontal",
    body: "A ascensão reta move a mira de leste a oeste, como a longitude em um mapa.",
  },
  {
    route: "/observatorio/",
    target: "obs-dec",
    title: "Mire na vertical",
    body: "A declinação move a mira para o norte ou para o sul, como a latitude. Achou algo? “Importar para o explorador” leva essas coordenadas para ver as fotos reais.",
  },
  {
    route: "/observatorio/",
    target: "obs-diario",
    title: "Diário de bordo",
    body: "Ele avisa quando a mira está chegando perto de um alvo. Ao descobrir um, clique no card para conhecer a história do astro.",
  },
  {
    route: "/observatorio/",
    target: "obs-tempo",
    title: "Controle o tempo",
    body: "Avance ou volte no tempo para ver a Terra girar na simulação.",
  },
  {
    target: "tour-help",
    title: "Pronto!",
    body: "Você pode rever este tutorial quando quiser por este botão. Bons céus!",
  },
];
