// Textos da tela /explorar. Alvos vêm de content/landing.ts.

export const explorar = {
  metaTitulo: "Explorar o céu · OxenTech",
  marcaSub: "Observatório Orbital",
  voltarRotulo: "Voltar para a página inicial",
  tituloSr: "Explorar o céu",

  abasRotulo: "Alvos em destaque",
  nomeCurto: {
    barnard: "Barnard",
    wise0855: "WISE 0855",
    "eps-indi-b": "Epsilon Indi B",
    "rw-aur": "RW Aurigae",
    "r-dra": "R Draconis",
  } as Record<string, string>,

  config: {
    abrir: "Configurações",
    titulo: "Configurações",
    marcar: "Destacar o alvo no visor",
    coordTitulo: "Ir para coordenadas (graus ICRS)",
    raRotulo: "RA",
    decRotulo: "Dec",
    raAjuda: "0 a 360",
    decAjuda: "−90 a +90",
    buscar: "Buscar",
    erroRa: "RA de 0 a 359,99.",
    erroDec: "Dec de −90 a +90.",
    atalhos: "Atalhos no visor: espaço = play/pausa · ← → = trocar época",
  },

  terra: {
    rotulo: "Rotação da Terra",
    eixo: "(RA)",
    slider: "Rotação da Terra (ascensão reta): arraste o ponto do arco ou use as setas",
  },

  satelite: {
    nome: "SPHEREx",
    arraste: "Inclinação do satélite (declinação): arraste o satélite para cima ou para baixo",
  },

  inclinacao: {
    titulo: "Inclinação do Satélite",
    sub: "(Dec)",
    rotulo: "Inclinação do satélite (declinação), de −90 a +90 graus",
  },

  visor: {
    titulo: "Visor SPHEREx",
    rotulo: "Visor: comparação de épocas",
    fov: (arcmin: number) => `${arcmin}′ × ${arcmin}′ · N↑`,
    vazioTitulo: "Aponte o satélite",
    vazioTexto: "Escolha um astro no topo ou gire a Terra e incline o satélite.",
    carregando: "Buscando fotos no arquivo do IRSA…",
    carregandoLento: "O servidor pode levar até 1 minuto para acordar.",
    sintetico: "Imagem sintética de teste · os recortes reais do SPHEREx entram aqui",
    fonte: "IRSA",
    semFonte: "sem link (teste)",
    detector: "detector",
    buscarAqui: "Buscar neste ponto",
    foraDeMira: "Você moveu o satélite",
  },

  tempo: {
    titulo: "Tempo",
    dataHora: "Data e Hora",
    mjd: "MJD",
    data: "Data da época (UTC)",
    hora: "Hora da época (UTC)",
    mjdRotulo: "Data juliana modificada da época",
    anterior: "Época anterior",
    proxima: "Próxima época",
    play: "Reproduzir épocas",
    pausar: "Pausar",
    linha: "Linha do tempo das épocas",
    semDados: "—",
  },

  detalhes: {
    titulo: "Detalhes da fonte",
    colecao: "Coleção",
    quadro: "Quadro",
    observado: "Observado em",
    comprimento: "Comprimento de onda",
    largura: "Largura de banda",
    detector: "Detector",
    cobertura: "Pixels válidos",
    calibracao: "Calibração",
    processamento: "Processamento",
    obtido: "Obtido do IRSA em",
    original: "Abrir original no IRSA ↗",
    recorte: "Baixar recorte FITS ↗",
  },

  erros: {
    coordenada_invalida: {
      titulo: "Coordenada inválida",
      texto: "Confira os valores de RA e Dec e tente de novo.",
    },
    sem_cobertura: {
      titulo: "Poucas fotos deste ponto",
      texto: "O SPHEREx ainda não tem duas fotos comparáveis deste campo. Tente um astro em destaque.",
    },
    indisponivel: {
      titulo: "O arquivo está demorando",
      texto: "A busca ao vivo está indisponível agora. Enquanto isso, abra um exemplo pronto.",
    },
    rede: {
      titulo: "Sem conexão com o servidor",
      texto: "Não deu para falar com a busca ao vivo. Abra um exemplo pronto enquanto isso.",
    },
    sem_api: {
      titulo: "Busca ao vivo em breve",
      texto: "A busca por qualquer ponto do céu ainda está sendo ligada. Por enquanto, explore os astros em destaque.",
    },
    exemplo_ausente: {
      titulo: "Exemplo indisponível",
      texto: "Os dados deste alvo ainda não foram preparados.",
    },
    abrirExemplo: "Abrir exemplo: Estrela de Barnard",
  } as const,

  creditos:
    "SPHEREx: NASA / JPL-Caltech / IPAC · IRSA DOI 10.26131/IRSA678 · 10.26131/IRSA662 · Terra: NASA Earth Observatory (Blue Marble, domínio público) · Ilustração do SPHEREx: NASA/JPL-Caltech (PIA26531) · Projeto independente, sem endosso da NASA",
};
