import type { Locale } from "../lib/i18n";

// Textos do widget "Achou algo diferente?". Conversa guiada (roteiro fixo, sem IA).
const pt = {
  bubble: "Achou algo diferente?",
  open: "Abrir assistente de descoberta",
  close: "Fechar assistente",
  title: "Assistente de descoberta",
  subtitle: "Vamos checar juntos",
  restart: "Recomeçar",
  copy: "Copiar",
  copied: "Copiado!",
  you: "Você",

  intro: "Oi! Suspeita de ter encontrado algo que não deveria estar ali? Vou te ajudar a descobrir se é uma descoberta de verdade.",
  introYes: "Sim, vi algo estranho",
  introHow: "Só quero saber como funciona",
  how: "Astrônomos amadores descobrem asteroides, cometas e estrelas variáveis todos os anos. O caminho é sempre o mesmo: 1) conferir se o objeto já é conhecido, 2) se não for, medir a posição com cuidado e 3) enviar um relatório ao Minor Planet Center (MPC), o órgão da União Astronômica Internacional que registra esses objetos.",
  howNext: "Quero checar algo agora",

  kind: "O que você notou entre as épocas?",
  kindMove: "Um ponto mudou de lugar",
  kindNew: "Apareceu um ponto novo",
  kindBright: "Um ponto mudou de brilho",
  kindUnsure: "Não sei dizer",

  unsure: "Antes de comemorar, descarte os impostores mais comuns: raios cósmicos (um ponto muito fino que aparece em uma só imagem), pixels quentes (ficam no mesmo pixel em todas as fotos), rastros de satélites (linhas retas) e reflexos de estrelas brilhantes. Se o ponto aparece em mais de uma época e parece uma estrela de verdade, vale investigar.",
  unsureNext: "Ainda acho que é algo real",

  field: "Estas são as informações do campo que você está vendo. Use-as nas consultas:",
  noField: "Abra um campo no Explorador para eu preencher as coordenadas automaticamente.",
  fieldName: "Campo",
  fieldDate: "Data (UTC)",

  check: "Passo 1: veja se já é conhecido. O MPChecker, do Minor Planet Center, lista todos os asteroides e cometas conhecidos perto dessa posição naquela data. Abra a busca já preenchida para cada época (raio de 5′, magnitude até 24).",
  checkOpenDate: "Buscar no MPChecker · {date} ↗",
  checkOpenBlank: "Abrir o formulário vazio e colar os dados ↗",
  checkSimbad: "Atenção: o MPChecker só conhece objetos do Sistema Solar (asteroides e cometas). Estrelas e anãs marrons próximas, como Barnard e Epsilon Indi B, também “andam” no céu, mas por movimento próprio, e não aparecem nele. Para essas, consulte o SIMBAD, que lista estrelas, anãs marrons e galáxias da região.",
  simbadOpen: "Consultar no SIMBAD ↗",
  simbadMirror: "Não abriu? Tente o servidor da França ↗",
  checkQuestion: "O MPChecker mostrou algum objeto conhecido nessa posição? (Se a página disser “No known minor planets… were found”, nenhum asteroide ou cometa conhecido estava ali.)",
  checkKnown: "Sim, já era conhecido",
  checkUnknown: "Não apareceu nada",

  known: "Então você reencontrou um objeto já catalogado. Isso não é pouco: é exatamente assim que os astrônomos confirmam órbitas! Anote o nome dele e compare com o que você viu. Quer procurar em outro campo?",
  knownAgain: "Checar outro objeto",

  bright: "Mudanças de brilho costumam ser estrelas variáveis. O catálogo oficial é o VSX, da AAVSO. Procure a posição lá e no SIMBAD: se a estrela não estiver marcada como variável, a AAVSO aceita relatos de novas variáveis.",
  brightOpen: "Abrir o VSX (AAVSO) ↗",

  unknown: "Nada catalogado nessa posição? Pode ser algo novo! Agora vem a parte rigorosa. Antes de montar o relatório, confira estes pontos:",
  rules: [
    "Meça a posição exata do objeto (não o centro do campo) com um programa como o Astrometrica ou o Tycho Tracker.",
    "Tenha pelo menos 3 observações na mesma noite. O MPC não aceita uma posição única nem medidas aproximadas.",
    "As imagens deste site são da SPHEREx, um telescópio espacial: o ideal é confirmar o objeto com observações próprias ou de um observatório parceiro.",
  ],
  unknownNext: "Entendi, montar o relatório",

  form: "Preencha seus dados. Se for sua primeira vez, deixe o código como XXX e peça um código de observatório ao MPC.",
  formCode: "Código do observatório",
  formContact: "Contato (nome e e-mail)",
  formObservers: "Observadores",
  formMeasurer: "Quem mediu",
  formTelescope: "Telescópio e câmera",
  formCodeHelp: "Como conseguir um código ↗",
  formSubmit: "Gerar relatório MPC",

  report: "Aqui está o rascunho no formato de 80 colunas do MPC. As linhas usam o centro do campo como posição: troque RA e Dec pelas posições medidas antes de enviar.",
  reportLabel: "Relatório MPC",
  reportEmail: "Enviar por e-mail ao MPC",
  reportAdes: "Formulário ADES do MPC ↗",
  reportNote: "Envie em texto puro (sem formatação nem quebra de linhas). Depois, acompanhe o recebimento no WAMO, o rastreador do MPC.",
  reportDone: "Pronto!",
  done: "Boa sorte, e bons céus! Se o MPC confirmar, seu nome entra para a história da astronomia.",
};

export type DiscoveryCopy = typeof pt;

const en: DiscoveryCopy = {
  bubble: "Found something odd?",
  open: "Open discovery assistant",
  close: "Close assistant",
  title: "Discovery assistant",
  subtitle: "Let's check it together",
  restart: "Start over",
  copy: "Copy",
  copied: "Copied!",
  you: "You",

  intro: "Hi! Do you suspect you found something that shouldn't be there? I'll help you figure out whether it's a real discovery.",
  introYes: "Yes, I saw something odd",
  introHow: "I just want to know how it works",
  how: "Amateur astronomers discover asteroids, comets and variable stars every year. The path is always the same: 1) check whether the object is already known, 2) if not, measure its position carefully and 3) send a report to the Minor Planet Center (MPC), the International Astronomical Union body that records these objects.",
  howNext: "I want to check something now",

  kind: "What did you notice between the epochs?",
  kindMove: "A point changed position",
  kindNew: "A new point appeared",
  kindBright: "A point changed brightness",
  kindUnsure: "I'm not sure",

  unsure: "Before celebrating, rule out the usual impostors: cosmic rays (a very sharp point in a single image), hot pixels (stuck on the same pixel in every image), satellite trails (straight lines) and reflections from bright stars. If the point shows up in more than one epoch and looks like a real star, it's worth investigating.",
  unsureNext: "I still think it's real",

  field: "Here is the information for the field you're viewing. Use it in the searches:",
  noField: "Open a field in the Explorer so I can fill in the coordinates for you.",
  fieldName: "Field",
  fieldDate: "Date (UTC)",

  check: "Step 1: see whether it's already known. The Minor Planet Center's MPChecker lists every known asteroid and comet near that position on that date. Open the pre-filled search for each epoch (5′ radius, magnitude down to 24).",
  checkOpenDate: "Search MPChecker · {date} ↗",
  checkOpenBlank: "Open the blank form and paste the data ↗",
  checkSimbad: "Note: MPChecker only knows Solar System objects (asteroids and comets). Nearby stars and brown dwarfs, such as Barnard's Star and Epsilon Indi B, also “move” across the sky, but through proper motion, and won't show up there. For those, check SIMBAD, which lists the stars, brown dwarfs and galaxies in the area.",
  simbadOpen: "Search SIMBAD ↗",
  simbadMirror: "Didn't open? Try the server in France ↗",
  checkQuestion: "Did MPChecker show a known object at that position? (If the page says “No known minor planets… were found”, no known asteroid or comet was there.)",
  checkKnown: "Yes, it was already known",
  checkUnknown: "Nothing showed up",

  known: "Then you recovered an object that is already catalogued. That's no small thing: it's exactly how astronomers confirm orbits! Note its name and compare it with what you saw. Want to look at another field?",
  knownAgain: "Check another object",

  bright: "Brightness changes are usually variable stars. The official catalog is AAVSO's VSX. Look up the position there and on SIMBAD: if the star isn't listed as variable, AAVSO accepts reports of new variables.",
  brightOpen: "Open VSX (AAVSO) ↗",

  unknown: "Nothing catalogued at that position? It may be something new! Now comes the rigorous part. Before building the report, check these points:",
  rules: [
    "Measure the object's exact position (not the field center) with software such as Astrometrica or Tycho Tracker.",
    "Have at least 3 observations on the same night. The MPC doesn't accept a single position or approximate measurements.",
    "The images on this site come from SPHEREx, a space telescope: ideally, confirm the object with your own observations or a partner observatory.",
  ],
  unknownNext: "Got it, build the report",

  form: "Fill in your details. If it's your first time, leave the code as XXX and ask the MPC for an observatory code.",
  formCode: "Observatory code",
  formContact: "Contact (name and e-mail)",
  formObservers: "Observers",
  formMeasurer: "Measurer",
  formTelescope: "Telescope and camera",
  formCodeHelp: "How to get a code ↗",
  formSubmit: "Generate MPC report",

  report: "Here is the draft in the MPC's 80-column format. The lines use the field center as the position: replace RA and Dec with your measured positions before sending.",
  reportLabel: "MPC report",
  reportEmail: "E-mail it to the MPC",
  reportAdes: "MPC ADES form ↗",
  reportNote: "Send it as plain text (no formatting or line wrapping). Then track its receipt in WAMO, the MPC's tracker.",
  reportDone: "Done!",
  done: "Good luck, and clear skies! If the MPC confirms it, your name goes down in astronomy history.",
};

export const discoveryCopy: Record<Locale, DiscoveryCopy> = { pt, en };
