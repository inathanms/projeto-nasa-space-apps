# Brief — Landing page OxenTech · Planet X and SPHEREx

Leia este arquivo inteiro antes de escrever código. Planner do projeto: `PLANO-MVP.md` (raiz do repo). Em caso de conflito, o PLANO-MVP manda.

## Contexto

- NASA Space Apps Challenge 2026, desafio **Planet X and SPHEREx**.
- Produto: site público onde curiosos e entusiastas de astronomia comparam imagens reais do telescópio SPHEREx (NASA) em épocas diferentes para ver o que se move ou muda de brilho.
- Equipe: **OxenTech** (Aracaju/SE). Identidade = sertão nordestino + espaço.
- Esta tarefa: **apenas a landing page (`/`)**. O explorador (`/explorar`) é outra tarefa; aqui só criar a rota com um placeholder.

## Stack (fixa, do PLANO-MVP)

- Next.js (App Router) + TypeScript.
- **Export estático**: `next.config.ts` com `output: "export"`; build gera `out/` (deploy no Cloudflare Pages).
- CSS puro (CSS Modules ou um `globals.css` com variáveis). Sem Tailwind, sem libs de UI.
- Sem fontes externas obrigatórias; usar `Inter` via `next/font/google` se quiser, com fallback `Arial, sans-serif`.
- Tudo dentro de `frontend/`.
nao
## Estrutura esperada

```
frontend/
  app/
    layout.tsx            html lang="pt-BR", metadata, fonte, globals.css
    globals.css           tokens (variáveis CSS) + reset
    page.tsx              landing: compõe as seções
    explorar/page.tsx     placeholder "Em construção" + link para "/"
  components/landing/
    Nav.tsx
    Hero.tsx              inclui o SVG do céu (estrelas, Touro, órbita, dunas, cacto)
    PorQue.tsx
    ComoFunciona.tsx
    Alvos.tsx
    Dados.tsx
    Sobre.tsx
    CtaFinal.tsx
    Footer.tsx
  content/landing.ts      TODOS os textos e a lista de alvos (nada de texto hardcoded nos componentes)
  public/brand/
    logo-oxentech-mark.png
    logo-oxentech-full.jpg
```

## Referências visuais (nesta pasta)

- `mockup-landing-oxentech.png` — resultado esperado (página inteira, 1440px).
- `referencia-mockup.html` — HTML/CSS estático do mockup. **Usar como referência de layout, cores, espaçamentos e SVG**, não copiar como está: converter para componentes React tipados.
- `assets/` — logos (copiar para `frontend/public/brand/`).

## Design tokens

```css
--night:  #0b1f22;  /* fundo principal (céu noturno) */
--night2: #0d2527;  /* fundo seção Dados */
--card:   #0f2a2c;  --card-border: #1f4a47;
--teal:   #2b7a6b;  /* cacto, botões secundários, números de passos */
--teal-l: #5fb3a1;  /* linhas da constelação, bordas de botão ghost */
--orange: #e0703a;  /* CTA principal, destaques, "kicker" */
--rust:   #c75636;  /* duna de trás */
--sun:    #eaa83a;  /* números, órbita, brilhos */
--cream:  #f7e1c9;  /* texto em fundo escuro e fundo das seções claras */
--text-muted-dark: #a9c6bd;   --text-on-cream: #1d3b37;
```

- Raios: cards 18px, botões 999px (pílula), CTA final 28px.
- Padding de seção: 96px vertical, 64px lateral (desktop).
- Tipografia: H1 64px/800, H2 40px/800, kicker 12px/700 com letter-spacing .14em, corpo 17–19px.
- Alternância de seções: escuro → escuro → **creme** → escuro → escuro(night2) → **creme** → CTA → footer.

## Seções e conteúdo (colocar em `content/landing.ts`)

**Nav** (fixa/absoluta no topo do hero): logo mark + "Oxen**Tech**" (Tech em laranja, peso normal) + subtítulo "CÉU DO SERTÃO · SPHEREx". Links âncora: Por que aqui (#por-que), Como funciona (#como-funciona), Alvos (#alvos), Dados (#dados), Quem somos (#sobre). Botão "Explorar o céu →" → `/explorar`.

**Hero** (#inicio, ~860px de altura)
- Tag: "NASA SPACE APPS 2026 · PLANET X AND SPHEREx"
- H1: "Do sertão,<br>veja o céu **se mover.**" (parte final em laranja)
- Texto: "Compare imagens reais do telescópio SPHEREx, da NASA, e descubra estrelas que andam, piscam e se escondem no infravermelho. Sem instalar nada. Sem precisar saber astronomia."
- Botões: "Explorar o céu →" (`/explorar`) e "Ver um exemplo" (`/explorar?alvo=barnard`).
- Números: **102** cores do infravermelho · **2×/ano** o céu inteiro mapeado · **100%** dados públicos da NASA.
- Arte SVG (lado direito/fundo): estrelas aleatórias **com seed fixa** (evitar hydration mismatch — gerar no build ou usar lista fixa), constelação do Touro com rótulo "CONSTELAÇÃO DO TOURO", órbita elíptica tracejada com satélite e rótulo "SPHEREx", estrela com rastro e círculo laranja "ela se moveu!", 3 camadas de dunas, cacto teal com circuitos.

**Por que aqui** (#por-que) — kicker "POR QUE AQUI", H2 "O céu que seus olhos não veem", lead "O SPHEREx fotografa o universo em luz infravermelha. A gente transforma esses dados em algo que qualquer curioso consegue explorar." 4 cards:
1. Veja o invisível — Imagens infravermelhas reais, de estrelas frias e poeira que nenhum telescópio comum mostra.
2. Compare épocas — Alterne entre fotos do mesmo ponto do céu com meses de diferença e veja o que mudou.
3. Histórias prontas — Comece pela estrela mais rápida do céu ou pela anã marrom mais fria já encontrada.
4. Ciência cidadã — Plutão foi achado comparando fotos. O próximo planeta pode ser achado por você.

**Como funciona** (#como-funciona, fundo creme) — H2 "Três passos, nenhum telescópio", lead "Você escolhe um ponto do céu, a gente busca as fotos no arquivo da NASA e alinha tudo para você comparar." Passos:
1. Escolha um alvo — Clique num astro em destaque, busque pelo nome ou digite as coordenadas.
2. Compare as épocas — Aperte play e alterne entre fotos tiradas com meses de diferença.
3. Descubra — O que pulou de lugar está se movendo. O que mudou de brilho está pulsando.

**Alvos** (#alvos) — kicker "ALVOS EM DESTAQUE", H2 "Comece por aqui", lead "Os alvos escolhidos pelo desafio da NASA, cada um com algo para você perceber." Cards clicáveis → `/explorar?alvo=<slug>`:

| slug | nome | texto | tag | RA/Dec (graus, J2000) |
|---|---|---|---|---|
| barnard | Estrela de Barnard | A estrela que mais anda no nosso céu. | movimento | 269.4521, +4.6934 |
| wise0855 | WISE 0855 | A anã marrom mais fria conhecida, mais fria que o Polo Norte. | movimento | 133.7951, −7.2451 |
| eps-indi-b | Epsilon Indi B | Duas "estrelas fracassadas" dançando juntas. | movimento | a preencher (TODO) |
| rw-aur | RW Aurigae | Uma estrela jovem que muda de brilho. | brilho | a preencher (TODO) |
| r-dra | R Draconis | Uma estrela que pisca ao longo dos meses. | brilho | a preencher (TODO) |

(O mockup mostra 4; incluir os 5 do desafio — grid de 5 ou 3+2.) Ilustração de cada card = pequeno SVG estilizado (sem foto real por enquanto). Guardar RA/Dec no `content/landing.ts`; os TODOs ficam como `null` com comentário.

**Dados** (#dados, fundo night2) — kicker "DE ONDE VÊM OS DADOS", H2 "Direto do arquivo da NASA", lead "Cada imagem vem do arquivo público do SPHEREx no NASA/IPAC IRSA, com data, detector, comprimento de onda e link para o original. Nada é simulado." Linha de crédito: "SPHEREx: NASA / JPL-Caltech / IPAC · IRSA DOI 10.26131/IRSA678 · 10.26131/IRSA662". Fluxo de 3 caixas: SPHEREx (órbita a 700 km) → IRSA (arquivo NASA) → OxenTech (alinha e mostra). Usar ícones SVG simples, não emoji.

**Quem somos** (#sobre, fundo creme) — logo mark grande (300px, anel creme). Kicker "QUEM SOMOS", H2 "OxenTech". Texto: "Somos uma equipe de Aracaju, Sergipe. O nome mistura o 'oxente' do nordeste com tecnologia, e o boi do nosso logo é a constelação do Touro, que brilha no céu do sertão." + "Acreditamos que olhar para o céu não depende de onde você está, só da curiosidade."

**CTA final** — faixa com gradiente teal → ferrugem: "Pronto para olhar para cima?" / "Escolha uma estrela e veja o que mudou." / botão creme "Explorar o céu →".

**Footer** — "© 2026 OxenTech · NASA Space Apps Challenge 2026" | "Dados: NASA/JPL-Caltech/IPAC via IRSA · Projeto independente, sem endosso da NASA".

## Regras obrigatórias

- **Não usar logo/marca da NASA** (meatball, worm) nem sugerir endosso. NASA aparece só como fonte de dados e nome do desafio.
- Créditos e DOIs do IRSA sempre visíveis (seção Dados + footer).
- Responsivo: funcionar em 375px (celular) e 1440px. No celular: nav vira menu simples (ou só logo + CTA), grids viram 1 coluna, arte do hero vai para trás do texto com opacidade reduzida.
- Acessibilidade: HTML semântico (`header`, `nav`, `main`, `section` com `aria-labelledby`, `footer`), contraste AA, foco visível, SVG decorativo com `aria-hidden="true"`, `alt` no logo.
- `prefers-reduced-motion`: se adicionar animação (ex.: estrela piscando, satélite na órbita), desligar com essa media query. Animações são opcionais.
- Sem dependências além de next/react/react-dom/typescript/@types.
- Links internos com `next/link`; `<img>` ou `next/image` com `unoptimized: true` (export estático).

## Critérios de aceite

- [ ] `npm run build` gera `frontend/out/` sem erros nem warnings de hydration.
- [ ] `/` reproduz o mockup (cores, ordem das seções, textos) em 1440px.
- [ ] Layout ok em 375px, 768px e 1440px.
- [ ] Âncoras da nav rolam até as seções; botões levam a `/explorar` (placeholder) e `/explorar?alvo=...`.
- [ ] Textos e alvos vêm de `content/landing.ts`.
- [ ] Nenhum logo da NASA; créditos IRSA presentes.

## Fora do escopo agora

Explorador funcional, chamada à API, imagens reais do SPHEREx, i18n, analytics, deploy.
