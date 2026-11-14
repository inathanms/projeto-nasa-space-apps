// Conquistas: aparecem quando a pessoa aponta o satélite (girando a Terra / inclinando)
// para perto de um dos alvos em destaque — sem precisar clicar em "Buscar".
// RA/Dec de cada alvo vêm de content/landing.ts (alvos).
//
// Fatos: só o que foi conferido. Campos com null aparecem como "a confirmar" na tela.
// Pendências de verificação ficam em `aConfirmar` (não aparecem para o público).

export type Conquista = {
  slug: string;
  titulo: string; // "Você achou …"
  resumo: string;
  descobridor: string | null;
  epoca: string | null;
  contexto: string;
  fatos: string[];
  /** notas internas para a equipe conferir antes da demo */
  aConfirmar?: string[];
};

export const conquistasUi = {
  nova: "NOVA CONQUISTA",
  denovo: "VOCÊ VOLTOU AQUI",
  descobridor: "Quem descobriu primeiro",
  epoca: "Época da descoberta",
  contexto: "Contexto histórico",
  fatos: "Fatos curiosos",
  aConfirmar: "a confirmar",
  verNoVisor: "Ver no visor",
  continuar: "Continuar explorando",
  fechar: "Fechar conquista",
  contador: (n: number, total: number) => `${n}/${total}`,
  contadorRotulo: (n: number, total: number) => `Conquistas: ${n} de ${total} alvos encontrados`,
  anuncio: (nome: string) => `Conquista! Você achou ${nome}.`,
  sinal: {
    rotulo: "Sinal",
    fraco: "fraco",
    medio: "médio",
    forte: "forte",
    dica: "Algo interessante por perto…",
  },
  abaConquistada: "encontrado",
};

/** distância angular (graus) para contar como "achou" */
export const RAIO_CONQUISTA = 4;
/** faixas do "quente/frio" (graus) */
export const SINAL = { fraco: 25, medio: 12, forte: 7 };

export const conquistas: Record<string, Conquista> = {
  barnard: {
    slug: "barnard",
    titulo: "Você achou a Estrela de Barnard!",
    resumo:
      "Uma anã vermelha a cerca de 6 anos-luz: o sistema estelar mais próximo depois de Alfa Centauri, e a estrela que mais anda no nosso céu.",
    descobridor: "Edward Emerson Barnard, astrônomo americano",
    epoca: "1916, no Observatório Yerkes (EUA)",
    contexto:
      "Barnard comparou fotografias da mesma região do céu tiradas com anos de diferença e percebeu que uma estrela fraca tinha mudado de lugar mais do que qualquer outra conhecida. É exatamente o que você faz neste site: comparar épocas.",
    fatos: [
      "Ela anda cerca de 10 segundos de arco por ano no céu: em uns 180 anos, percorre o tamanho da Lua cheia.",
      "É fraca demais para ser vista a olho nu, mesmo estando tão perto.",
      "Nos anos 1960, um astrônomo anunciou planetas em volta dela, mas era erro do instrumento. Só em 2025 quatro planetas pequenos foram confirmados de verdade.",
      "Ela está se aproximando: daqui a uns 10 mil anos será a estrela mais próxima do Sol.",
    ],
    aConfirmar: ["Ano exato da aproximação máxima (~11.800 d.C.) e distância nessa época (~3,8 anos-luz)."],
  },
  wise0855: {
    slug: "wise0855",
    titulo: "Você achou WISE 0855!",
    resumo:
      "A anã marrom mais fria já encontrada, a cerca de 7,3 anos-luz: um objeto entre planeta e estrela, quase sem luz própria.",
    descobridor: "Kevin Luhman, astrônomo da Universidade Estadual da Pensilvânia (EUA)",
    epoca: "2014, com dados do telescópio espacial WISE",
    contexto:
      "Luhman achou WISE 0855 comparando imagens infravermelhas do WISE tiradas em épocas diferentes: o ponto se movia rápido demais para estar longe. Foi a mesma ideia de comparar fotos, agora com um telescópio que mapeou o céu inteiro em infravermelho, como o SPHEREx faz hoje.",
    fatos: [
      "A temperatura dela fica por volta de 250 kelvin, uns −23 °C: mais ou menos a de um freezer.",
      "É tão fria e fraca que praticamente só aparece em luz infravermelha.",
      "Ela se move cerca de 8 segundos de arco por ano no céu, um dos movimentos mais rápidos já medidos.",
      "Está entre os vizinhos mais próximos do Sol, mas só foi notada no século XXI.",
    ],
  },
  "eps-indi-b": {
    slug: "eps-indi-b",
    titulo: "Você achou Epsilon Indi B!",
    resumo:
      "Duas anãs marrons que giram uma em volta da outra, presas à estrela Epsilon Indi A, a cerca de 12 anos-luz, na constelação do Índio.",
    descobridor: "Equipe de Ralf-Dieter Scholz (Instituto de Astrofísica de Potsdam, Alemanha)",
    epoca: "2003; em seguida se descobriu que era um par (Ba e Bb)",
    contexto:
      "Epsilon Indi A é visível a olho nu no céu do hemisfério sul há milênios. Mas a companheira fria só apareceu quando grandes levantamentos digitais do céu passaram a procurar objetos fracos que se moviam junto com estrelas conhecidas.",
    fatos: [
      "Ba e Bb são “estrelas fracassadas”: não têm massa suficiente para fundir hidrogênio como o Sol.",
      "Como o par está bem perto, os astrônomos conseguem medir a massa de cada uma, o que é raro para anãs marrons.",
      "A estrela principal, Epsilon Indi A, também tem um planeta gigante e frio, fotografado pelo telescópio James Webb.",
    ],
    aConfirmar: [
      "Descoberta de Ba por Scholz et al. (2003) e do par Ba/Bb por McCaughrean et al. (2003/2004): conferir nos artigos.",
      "Imagem do planeta Epsilon Indi Ab pelo JWST (2024): conferir referência.",
    ],
  },
  "rw-aur": {
    slug: "rw-aur",
    titulo: "Você achou RW Aurigae!",
    resumo:
      "Uma estrela muito jovem, com alguns milhões de anos, ainda cercada pelo disco de gás e poeira onde planetas podem se formar. Fica na constelação do Cocheiro.",
    descobridor: null,
    epoca: null,
    contexto:
      "RW Aurigae é um “bebê” parecido com o Sol na infância, do tipo T Tauri. Em 2010 o brilho dela despencou por cerca de 180 dias. Em 2014–2015 veio um apagão ainda mais fundo, de mais de 2 magnitudes. A explicação mais aceita é poeira passando na frente, talvez de um disco bagunçado pela passagem da estrela companheira.",
    fatos: [
      "Ela tem uma companheira, RW Aurigae B: o par já se “esbarrou” e deixou um braço de matéria arrancado do disco.",
      "O brilho varia de um dia para o outro, por causa do gás que cai na estrela formando pontos quentes.",
      "Estudar estrelas assim ajuda a entender como era o Sol quando a Terra estava nascendo.",
    ],
    aConfirmar: [
      "Quem descobriu a variabilidade e em que ano (GCVS/AAVSO VSX).",
      "Distância (~500 anos-luz pela Gaia): conferir.",
    ],
  },
  "r-dra": {
    slug: "r-dra",
    titulo: "Você achou R Draconis!",
    resumo:
      "Uma gigante vermelha no fim da vida, na constelação do Dragão. Ela pulsa: incha e encolhe, mudando muito de brilho a cada ~8 meses.",
    descobridor: null,
    epoca: null,
    contexto:
      "R Draconis é uma variável do tipo Mira, o nome vem da estrela Mira, a primeira desse tipo a ser percebida, em 1596. Estrelas assim foram descobertas comparando o brilho noite após noite, muito antes de existirem fotografias.",
    fatos: [
      "O ciclo de brilho dura cerca de 246 dias.",
      "No auge chega à magnitude 6,7 (quase visível a olho nu) e no mínimo cai para 13,2: fica centenas de vezes mais fraca.",
      "É assim que o Sol deve ficar daqui a bilhões de anos, antes de soltar as camadas de fora.",
    ],
    aConfirmar: ["Quem descobriu a variabilidade de R Draconis e em que ano (GCVS/AAVSO VSX).", "Ano de Mira (1596, David Fabricius): conferir."],
  },
};
