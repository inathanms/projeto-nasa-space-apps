---
title: SPHEREye — Image API v0.1: qualidade de imagem (tamanho, upscale, RGB e empilhamento)
version: 0.1
date_created: 2026-11-14
last_updated: 2026-11-14
owner: Time do hackathon NASA (backend)
tags: [tool, api, python, fastapi, astronomy, spherex, image-processing]
---

# Introdução

Esta especificação **complementa** `spec/spec-tool-spherex-image-api.md` (doravante "spec base"). Ela altera e estende a rota `GET /image` para produzir imagens de maior qualidade visual para um público leigo, sem inventar informação que não existe nos dados.

Tudo que não for alterado aqui continua valendo como definido na spec base: arquitetura, camadas, configuração, formato de erros, segurança e testes.

A implementação é dividida em duas fases, que devem ser entregues **nesta ordem**, cada uma com seus testes passando antes de iniciar a próxima:

- **Fase A — Tamanho e upscale:** campo de visão maior e ampliação suave da imagem.
- **Fase B — Cor e empilhamento:** composição RGB com três detectores e combinação (mediana) das exposições de uma mesma visita.

## 1. Propósito e escopo

**Propósito:** guiar o agente de implementação na evolução de `GET /image`.

**Dentro do escopo:**

- Novos limites e defaults de `size`.
- Parâmetro `upscale`.
- Parâmetros `mode`, `detectors`, `scale_mins`, `scale_maxs` e `stack`.
- Orçamento de processamento por requisição.
- Novos headers e códigos de erro.
- Testes para todos os itens acima.

**Fora do escopo:**

- Cache (spec própria, futura).
- Super-resolução por IA, deconvolução, remoção de estrelas ou qualquer técnica que crie detalhe inexistente nos dados.
- Mudanças em `GET /epochs` além da reutilização da lógica de agrupamento de visits (seção 4.5).
- Frontend.

**Premissa física (deve constar no OpenAPI de `/image`):** cada pixel do SPHEREx cobre 6,15″ do céu. Isso é uma característica do instrumento (projetado para espectroscopia de todo o céu, não para fotos de alta resolução). Aumentar `size` mostra **mais céu**, não mais detalhe. `upscale` só suaviza a apresentação, não adiciona informação.

## 2. Definições

Termos da spec base continuam válidos. Novos termos:

| Termo | Definição |
|---|---|
| **Campo de visão (FOV)** | Lado do quadrado de céu exibido, em graus (`size`). |
| **Upscale** | Reamostragem da imagem final para um número maior de pixels usando filtro Lanczos. Não adiciona informação. |
| **Lanczos** | Filtro de interpolação de alta qualidade para redimensionamento de imagens. |
| **Alfa pré-multiplicado** | Representação RGBA em que os canais de cor são multiplicados pelo alfa antes do redimensionamento, evitando halos escuros nas bordas transparentes. No Pillow: modo `RGBa`. |
| **Composição RGB** | Imagem colorida em que os canais vermelho, verde e azul vêm de três detectores diferentes. É uma representação de "cor falsa": o infravermelho é invisível ao olho humano. |
| **Canal** | Cada uma das três imagens (R, G, B) de uma composição RGB. |
| **Frame** | Uma imagem individual (uma observation + um detector) já reprojetada para a grade de destino. |
| **Empilhamento (stack)** | Combinação pixel a pixel de vários frames da mesma visita e do mesmo detector, usando a mediana, para reduzir ruído. |
| **Observation de referência** | A observation indicada por `observation_id` na requisição. Define a visit usada no RGB e no empilhamento e o horário reportado. |
| **Par de detectores** | D1+D4, D2+D5 ou D3+D6: os detectores que cobrem um mesmo ponto do céu numa exposição (seção 7). |
| **Âncora do canal** | Em `rgb`, a observation da visit da referência que tem o detector do canal e é a mais próxima no tempo da referência (empate → a mais antiga). A própria referência vence quando tem o detector. Em `single`, a âncora é a referência. |
| **Fundo (background)** | Nível de brilho do céu sem fontes, estimado pela mediana com sigma-clipping. |
| **Sigma-clipping** | Estimativa estatística que descarta iterativamente valores extremos (estrelas, pixels ruins) antes de calcular mediana e desvio padrão. |

## 3. Requisitos, restrições e diretrizes

### 3.1 Fase A — Tamanho e upscale

- **REQ-101**: O default de `size` passa de `0.25` para `1.0` grau. O limite passa de `0.01 <= size <= 1.0` para `0.01 <= size <= 3.0`.
- **REQ-102**: O tamanho do cutout pedido ao IRSA deve ser calculado em **pixels**, não em graus: `fetch_px = min(ceil(size * F * 3600 / 6.15), 2040)`, com `F = 1.5` quando `align=true` e `F = 1.0` quando `align=false`. O parâmetro enviado ao IRSA é `size={fetch_px}pix`. Isso substitui o passo 4 do pipeline da spec base.
- **REQ-103**: Novo parâmetro `upscale` (inteiro, `1 <= upscale <= 4`, default `1`). Quando `> 1`, a imagem RGBA final é redimensionada para `(n * upscale) × (n * upscale)` com filtro Lanczos, **em alfa pré-multiplicado**: converter para `RGBa`, redimensionar, converter de volta para `RGBA`.
- **REQ-104**: O lado da imagem de saída (`n * upscale`) não pode passar de `MAX_OUTPUT_EDGE_PX` (env, default `4096`). Se passar → `422 REQUEST_TOO_LARGE`, com `details` contendo `requested_edge_px`, `max_edge_px` e uma sugestão (`"reduce size or upscale"`).
- **REQ-105**: Os headers de `/image` passam a refletir a imagem final: `X-Image-Width`/`X-Image-Height` = `n * upscale`; `X-Pixel-Scale-Arcsec` = `6.15 / upscale`. Novos headers: `X-Upscale` (inteiro) e `X-Native-Pixel-Scale-Arcsec` (sempre `6.15`).
- **REQ-106**: O limite `IRSA_MAX_CUTOUT_BYTES` passa de 50 MB para `104857600` (100 MB), porque um cutout de 2040 px contém o MEF quase completo (~70 MB).
- **REQ-107**: Com `align=false`, o `size` efetivo é limitado pelo cutout: se o IRSA devolver uma imagem menor que a pedida (posição perto da borda), usar o que veio, sem erro. Os headers devem refletir as dimensões reais.

### 3.2 Fase B — Composição RGB

- **REQ-201**: Novo parâmetro `mode` (enum: `single`, `rgb`; default `single`). Com `single`, o comportamento é o da spec base com as mudanças da Fase A.
- **REQ-202**: Novo parâmetro `detectors` (string com 3 detectores distintos separados por vírgula, na ordem **R,G,B**). Default quando `mode=rgb`: `D3,D2,D1`, seguindo a convenção astronômica de comprimento de onda maior = vermelho.
- **REQ-203**: Regras de combinação de parâmetros (violação → `422 VALIDATION_ERROR`):
  - `mode=single` exige `detector` e proíbe `detectors`, `scale_mins` e `scale_maxs`.
  - `mode=rgb` proíbe `detector`, `scale_min` e `scale_max`.
  - `mode=rgb` exige `align=true`.
  - `detectors` deve ter exatamente 3 valores distintos de `D1`–`D6`.
- **REQ-204**: Cada canal vem da sua **âncora** (seção 2), escolhida entre as observations da visit da referência, e é processado de forma independente pelos passos de cutout, ZODI, máscara e reprojeção da spec base, gerando três arrays float na **mesma grade de destino**. Os canais podem, portanto, vir de exposições diferentes, separadas por horas ou dias.
- **REQ-205**: Escala por canal: por padrão, percentis (`percentile_low`/`percentile_high`) calculados separadamente em cada canal. Novos parâmetros opcionais `scale_mins` e `scale_maxs` (3 floats cada, separados por vírgula, ordem R,G,B, em MJy/sr). Se um for informado, o outro também é obrigatório, e cada `min < max`.
- **REQ-206**: Stretch: o mesmo `stretch` é aplicado a cada canal normalizado. Os canais são então combinados em uma imagem RGB uint8. O parâmetro `colormap` é **ignorado** em `mode=rgb`; isso deve estar escrito na descrição do parâmetro no OpenAPI.
- **REQ-207**: Transparência em RGB: alfa = 0 onde **qualquer** canal for NaN.
- **REQ-208**: Se **nenhuma** observation da visit da referência tiver um ou mais dos detectores pedidos → `404 DETECTOR_NOT_AVAILABLE`, com `details.missing_detectors` (lista) e `details.available_detectors` (detectores presentes na visit, ordenados). O cliente evita esse 404 usando `visits[].rgb_available` (e `visits[].detectors`) de `/epochs`: escolhe uma visit com `rgb_available=true` e passa qualquer `observation_id` dela. Em `single` nada muda: a referência precisa ter o `detector` (senão `404 OBSERVATION_NOT_FOUND`).
- **REQ-209**: Em `mode=rgb`, os headers com valor por canal passam a ter 3 valores separados por vírgula, na ordem R,G,B, vindos da âncora de cada canal: `X-Detector` (ex.: `D3,D2,D1`), `X-Wavelength-Min-Um`, `X-Wavelength-Max-Um`, `X-Scale-Min`, `X-Scale-Max`. `X-Observation-Id`/`X-Observation-Time` continuam sendo os da referência. Novos headers só em `rgb`: `X-Channel-Observation-Ids` (ids das âncoras, R,G,B) e `X-Channel-Time-Span-Seconds` (do menor `t_min` ao maior `t_max` das âncoras). Novo header `X-Mode` (`single` ou `rgb`) em todas as respostas de `/image`.
- **REQ-210**: Os três cutouts de uma composição RGB devem ser baixados de forma concorrente, limitada por `CUTOUT_FETCH_CONCURRENCY` (env, default `3`).

### 3.3 Fase B — Empilhamento

- **REQ-301**: Novo parâmetro `stack` (bool, default `false`). Quando `true`, exige `align=true` (senão `422 VALIDATION_ERROR`). Vale para `mode=single` e para `mode=rgb` (neste caso, por canal).
- **REQ-302**: Seleção dos frames:
  1. Usar as linhas do SIA já obtidas no passo de resolução (mesma consulta por posição e coleção).
  2. Agrupar em observations e visits com **a mesma função usada por `/epochs`** (seção 4.5).
  3. Identificar a visit da observation de referência.
  4. Por canal, selecionar as observations dessa visit que tenham o detector do canal.
  5. Se houver mais que `STACK_MAX_EXPOSURES` (env, default `8`), manter as mais próximas no tempo da **referência**; a âncora do canal (em `single`, a própria referência) está sempre incluída.
- **REQ-303**: Combinação, por detector:
  1. Para cada frame, estimar o fundo com `astropy.stats.sigma_clipped_stats(frame, sigma=3.0, maxiters=5)` e subtrair a mediana do fundo.
  2. Combinar com `numpy.nanmedian` ao longo do eixo dos frames.
  3. Somar de volta a mediana dos fundos estimados.
  4. Pixels que são NaN em todos os frames continuam NaN.
- **REQ-304**: Com apenas 1 frame disponível, o resultado é o próprio frame. Isso não é erro e deve ser indicado pelo header `X-Stack-Count: 1`.
- **REQ-305**: Novos headers quando `stack=true`: `X-Stack-Count` (inteiro; em RGB, 3 valores R,G,B) e `X-Stack-Observation-Ids` (ids usados, separados por vírgula; em RGB, a união ordenada no tempo). `X-Observation-Time` continua sendo o da observation de referência. Novo header `X-Stack-Time-Span-Seconds` (diferença entre o primeiro `t_min` e o último `t_max` dos frames usados).
- **REQ-306**: A descrição de `stack` no OpenAPI deve dizer explicitamente: *"Median stacking suppresses objects that move between exposures (asteroids, comets). Use stack=false to look for moving objects."*

### 3.4 Orçamento de processamento

- **REQ-401**: Antes de qualquer download, calcular `total_cutouts` (número de cutouts necessários: canais × frames) e `fetch_pixels = total_cutouts * fetch_px²`.
- **REQ-402**: Se `total_cutouts > MAX_CUTOUTS_PER_REQUEST` (env, default `12`) ou `fetch_pixels > MAX_FETCH_PIXELS_PER_REQUEST` (env, default `16646400`, ou seja 4 × 2040²), reduzir primeiro a quantidade de frames do stack (mantendo as âncoras e os mais próximos no tempo) até caber. Se ainda não couber com 1 frame por canal → `422 REQUEST_TOO_LARGE`, com `details` contendo `total_cutouts`, `fetch_pixels`, os limites e a sugestão `"reduce size, disable stack, or use mode=single"`.
- **REQ-403**: Quando o número de frames for reduzido pelo orçamento, incluir o header `X-Stack-Truncated: true`.
- **REQ-404**: O semáforo `MAX_CONCURRENT_RENDERS` da spec base continua contando **uma vaga por requisição**, independentemente de quantos cutouts ela use.
- **REQ-405**: Liberar memória cedo: depois de reprojetar um frame, descartar os bytes do cutout e os objetos HDU (`hdul.close()`, remover referências). Não manter mais de `CUTOUT_FETCH_CONCURRENCY` cutouts brutos em memória ao mesmo tempo.

### 3.5 Restrições

- **CON-101**: Proibido usar qualquer modelo de IA ou técnica generativa para aumentar resolução ou "melhorar" a imagem.
- **CON-102**: A reprojeção usa sempre a escala nativa de 6,15″/px. O upscale acontece apenas no final, sobre a imagem RGBA.
- **CON-103**: Nenhuma nova dependência de provedor de nuvem. Novas dependências permitidas: nenhuma além das já listadas na spec base (`astropy.stats` faz parte do astropy; Pillow já é dependência).
- **CON-104**: A ordem dos canais em parâmetros e headers é sempre R,G,B.

### 3.6 Diretrizes

- **GUD-101**: Criar módulos novos em `app/processing/`: `stacking.py` (apenas a combinação dos frames; a seleção fica no serviço), `composite.py` (montagem RGB) e `resample.py` (upscale). A seleção de frames fica em `app/services/image_service.py`, reutilizando o agrupamento de `epochs_service.py`.
- **GUD-102**: Extrair o agrupamento observations/visits para uma função pura reutilizável, por exemplo `group_into_visits(records, gap_days) -> list[Visit]`, usada por `/epochs` e por `/image`.
- **GUD-103**: Registrar nos logs, por requisição: `mode`, `stack`, `total_cutouts`, `fetch_px`, duração de cada download, duração da reprojeção por frame e duração total.
- **GUD-104 (infra, sem código específico)**: Documentar no README que composições RGB e stacks com `size` grande usam centenas de MB de RAM. Instâncias com 512 MB devem usar `MAX_CONCURRENT_RENDERS=1` e limites de orçamento menores; o recomendado é ≥ 2 GiB.

## 4. Interfaces e contratos de dados

### 4.1 `GET /image` — tabela completa de parâmetros (v1.1)

| Param | Tipo | Default | Fase | Regra |
|---|---|---|---|---|
| `ra` | float | — | base | obrigatório |
| `dec` | float | — | base | obrigatório |
| `observation_id` | string | — | base | obrigatório |
| `mode` | enum `single`\|`rgb` | `single` | B | |
| `detector` | enum | — | base | obrigatório se `mode=single`; proibido se `mode=rgb` |
| `detectors` | string `Dx,Dy,Dz` | `D3,D2,D1` (só em rgb) | B | 3 distintos; proibido em `single` |
| `collection` | enum | env | base | |
| `size` | float (graus) | **`1.0`** | **A** | `0.01–3.0` |
| `upscale` | int | `1` | A | `1–4`; lado final ≤ `MAX_OUTPUT_EDGE_PX` |
| `align` | bool | `true` | base | deve ser `true` se `mode=rgb` ou `stack=true` |
| `stack` | bool | `false` | B | |
| `subtract_zodi` | bool | `true` | base | |
| `stretch` | enum | `asinh` | base | |
| `colormap` | enum | `inferno` | base | ignorado em `rgb` |
| `percentile_low` | float | `1.0` | base | |
| `percentile_high` | float | `99.5` | base | |
| `scale_min` / `scale_max` | float | — | base | só em `single` |
| `scale_mins` / `scale_maxs` | string `a,b,c` | — | B | só em `rgb` |

### 4.2 Headers de resposta (v1.1)

| Header | `single` | `rgb` |
|---|---|---|
| `X-Mode` | `single` | `rgb` |
| `X-Observation-Id` | id | id (referência) |
| `X-Observation-Time` | ISO | ISO (referência) |
| `X-Detector` | `D2` | `D3,D2,D1` (das âncoras) |
| `X-Channel-Observation-Ids` | — | 3 ids (âncoras, R,G,B) |
| `X-Channel-Time-Span-Seconds` | — | float (do menor `t_min` ao maior `t_max` das âncoras) |
| `X-Wavelength-Min-Um` / `X-Wavelength-Max-Um` | 1 valor | 3 valores (das âncoras) |
| `X-Scale-Min` / `X-Scale-Max` | 1 valor | 3 valores |
| `X-Image-Width` / `X-Image-Height` | `n*upscale` | `n*upscale` |
| `X-Upscale` | int | int |
| `X-Pixel-Scale-Arcsec` | `6.15/upscale` | `6.15/upscale` |
| `X-Native-Pixel-Scale-Arcsec` | `6.15` | `6.15` |
| `X-Valid-Pixel-Fraction` | float | float |
| `X-Stack-Count` | int (se `stack`) | 3 ints (se `stack`) |
| `X-Stack-Observation-Ids` | lista (se `stack`) | lista (se `stack`) |
| `X-Stack-Time-Span-Seconds` | float (se `stack`) | float (se `stack`) |
| `X-Stack-Truncated` | `true` (se reduzido) | `true` (se reduzido) |

Todos os novos headers devem ser adicionados a `Access-Control-Expose-Headers` e documentados no OpenAPI.

### 4.3 Novos códigos de erro

| HTTP | `code` | Quando |
|---|---|---|
| 404 | `DETECTOR_NOT_AVAILABLE` | Em `rgb`, nenhuma observation da visit da referência tem algum detector pedido. |
| 422 | `REQUEST_TOO_LARGE` | Lado final > `MAX_OUTPUT_EDGE_PX`, ou orçamento de cutouts/pixels excedido mesmo com 1 frame por canal. |

### 4.4 Novas variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `MAX_OUTPUT_EDGE_PX` | `4096` | REQ-104 |
| `CUTOUT_FETCH_CONCURRENCY` | `3` | REQ-210, REQ-405 |
| `STACK_MAX_EXPOSURES` | `8` | REQ-302 |
| `MAX_CUTOUTS_PER_REQUEST` | `12` | REQ-402 |
| `MAX_FETCH_PIXELS_PER_REQUEST` | `16646400` | REQ-402 |
| `IRSA_MAX_CUTOUT_BYTES` | **`104857600`** | alterado (REQ-106) |

Atualizar `backend/.env.example` e o README.

### 4.5 Pipeline de `/image` (v1.1)

```text
1. validar parâmetros e combinações (REQ-203, REQ-301)
2. SIA por posição + coleção  → linhas
3. localizar observation de referência e sua visit (404 OBSERVATION_NOT_FOUND)
4. canais = [detector] (single) | detectors (rgb); âncora por canal (seção 2) ou 404
   (single: OBSERVATION_NOT_FOUND se a referência não tem o detector; rgb: DETECTOR_NOT_AVAILABLE)
5. frames por canal = [âncora] (stack=false) | seleção REQ-302 (stack=true)
6. calcular fetch_px (REQ-102) e orçamento (REQ-401/402); reduzir frames ou 422
7. calcular n = round(size*3600/6.15) (mín. 16) e lado final n*upscale; checar MAX_OUTPUT_EDGE_PX (422)
8. adquirir vaga no semáforo (503 SERVER_BUSY)
9. para cada canal:
     baixar cutouts (concorrência limitada) → ZODI → máscara → reprojeção → float[n×n] por frame
     stack ? combinar (REQ-303) : único frame
10. escala por canal (percentis ou scale_min(s)/max(s))
11. stretch por canal
12. single → colormap → RGBA | rgb → empilhar R,G,B → RGBA (alfa REQ-207)
13. flip vertical
14. upscale Lanczos em RGBa pré-multiplicado (REQ-103)
15. PNG + headers (4.2)
```

## 5. Critérios de aceitação

### Fase A

- **AC-101**: Dado `size` omitido, quando chamo `/image` (single, align), então a imagem tem 585×585 px (`round(1.0*3600/6.15)`).
- **AC-102**: Dado `size=3.0`, então o cutout pedido ao IRSA usa `size=2040pix` (limite) e a imagem tem 1756×1756 px.
- **AC-103**: Dado `size=3.1` ou `size=0.005`, então `422 VALIDATION_ERROR`.
- **AC-104**: Dado `size=1.0&upscale=2`, então a imagem tem 1170×1170 px, `X-Upscale: 2`, `X-Pixel-Scale-Arcsec: 3.075` e `X-Native-Pixel-Scale-Arcsec: 6.15`.
- **AC-105**: Dado `size=3.0&upscale=4` (lado 7024 > 4096), então `422 REQUEST_TOO_LARGE` sem nenhuma chamada ao IRSA.
- **AC-106**: Dada uma imagem sintética com metade transparente e metade branca opaca, quando aplico `upscale=4`, então nenhum pixel opaco da borda entre as regiões tem luminância menor que 90% do branco (sem halo escuro, prova do alfa pré-multiplicado).
- **AC-107**: Dado `align=false` e um cutout sintético de 300×200 px (perto da borda), então a resposta tem 300×200 px (× upscale) e não há erro.

### Fase B — RGB

- **AC-201**: Dado `mode=rgb` sem `detectors`, então são usados `D3,D2,D1` e `X-Detector: D3,D2,D1`; cada canal vem da observation mais próxima no tempo da referência que tem aquele detector (`X-Channel-Observation-Ids`).
- **AC-202**: Dados três canais sintéticos em que só o canal R tem uma estrela em (x, y), quando renderizo em rgb, então o pixel correspondente no PNG tem R alto e G, B baixos.
- **AC-203**: Dado `mode=rgb&detector=D2`, ou `mode=rgb&align=false`, ou `mode=single&detectors=D1,D2,D3`, ou `detectors=D1,D1,D2`, ou `detectors=D1,D2`, então `422 VALIDATION_ERROR`.
- **AC-204**: Dada uma visit em que nenhuma observation tem D3, quando peço `mode=rgb&detectors=D3,D2,D1` com uma referência dessa visit, então `404 DETECTOR_NOT_AVAILABLE` com `missing_detectors: ["D3"]`. Se a referência não tem D3 mas outra observation da visit tem, a resposta é `200`.
- **AC-205**: Dados `scale_mins=0,0,0&scale_maxs=10,20,30`, então `X-Scale-Min: 0.0,0.0,0.0` e `X-Scale-Max: 10.0,20.0,30.0`.
- **AC-206**: Dado um pixel NaN apenas no canal G, então esse pixel tem alfa 0.
- **AC-207**: Dados os 3 downloads de cutout mockados com atraso de 1 s cada e `CUTOUT_FETCH_CONCURRENCY=3`, então o tempo total de download é < 2 s.

### Fase B — Stack

- **AC-301**: Dada uma visit sintética com 5 observations, cada uma com ruído independente sobre o mesmo céu, quando renderizo com `stack=true`, então o desvio padrão do fundo do resultado (antes do stretch) é menor que 60% do de um frame isolado, e `X-Stack-Count: 5`.
- **AC-302**: Dado um "asteroide" sintético que aparece em posições diferentes em cada um de 5 frames, quando faço o stack, então ele não aparece no resultado (pixel abaixo de 3σ do fundo). Isso valida o comportamento documentado em REQ-306.
- **AC-303**: Dados 5 frames com fundos de 1, 2, 3, 4 e 5 MJy/sr e o mesmo céu, então o resultado não apresenta degraus de fundo e seu fundo mediano ≈ 3 MJy/sr (±5%).
- **AC-304**: Dada uma visit com 12 observations com o detector pedido e `STACK_MAX_EXPOSURES=8`, então são usados 8 frames, incluindo a referência e os 7 mais próximos no tempo.
- **AC-305**: Dada uma visit com apenas a referência, então `200`, `X-Stack-Count: 1` e imagem idêntica à de `stack=false`.
- **AC-306**: Dado `stack=true&align=false`, então `422 VALIDATION_ERROR`.
- **AC-307**: Dado `mode=rgb&stack=true&size=3.0` com 8 observations na visit, então o orçamento reduz os frames (`fetch_px=2040`: no máximo 4 cutouts cabem em `MAX_FETCH_PIXELS_PER_REQUEST`) e, como 1 frame por canal (3 cutouts) cabe no limite, a resposta é `200` com `X-Stack-Count: 1,1,1` e `X-Stack-Truncated: true`.
- **AC-308**: Dado um orçamento em que nem 1 frame por canal cabe (ex.: `MAX_CUTOUTS_PER_REQUEST=2` com rgb), então `422 REQUEST_TOO_LARGE` sem downloads.
- **AC-309**: Observations de **outras** visits da mesma posição nunca entram no stack.

## 6. Estratégia de testes automatizados

- Reutilizar a fixture de FITS sintético da spec base, estendida para:
  - gerar N frames com o mesmo céu, ruído independente, fundos diferentes e pequenas diferenças de WCS (deslocamento de alguns pixels e rotação de alguns graus), simulando exposições de uma visit;
  - gerar um objeto móvel (posição diferente por frame);
  - gerar canais D1–D6 da mesma observation com fontes distintas por canal.
- Fixture VOTable sintética `sia_visit_multi.xml` com: 2 visits separadas por ~180 dias; a primeira com 12 observations a ~4 min de intervalo, cada uma com **um par** de detectores (D1+D4, D2+D5, D3+D6 alternando; uma delas com só D2); a segunda com 4 observations só com D1+D4 / D2+D5 (sem D3 na visit inteira, para AC-204). Testes de stack que precisam de mais de 4 frames do mesmo detector acrescentam linhas sintéticas a partir dela.
- Testes unit para `resample.py` (dimensões, AC-106), `composite.py` (AC-202, AC-206), `stacking.py` (AC-301 a AC-303, AC-305) e para a seleção/orçamento (AC-304, AC-307, AC-308, AC-309).
- Testes de integração das rotas com `respx` para AC-101 a AC-105, AC-201 a AC-205, AC-207 e AC-306.
- Teste live opcional (`@pytest.mark.live`): M101 em `mode=rgb&stack=true&size=1.0` retorna PNG colorido; registrar duração e pico de memória (`tracemalloc` ou `resource.getrusage`) no output do teste.
- Cobertura mínima continua 80% em `app/processing` e `app/services`.

## 7. Justificativa e contexto

- **Por que a resolução é limitada**: 6,15″/px é uma propriedade do SPHEREx. Uma galáxia como M101 (~28′) ocupa ~270 px mesmo sem recorte. A forma honesta de oferecer imagens impressionantes é usar campos maiores (regiões extensas como nebulosas e a Via Láctea), cor e redução de ruído, não inventar detalhe.
- **Por que `size` default 1°**: equilibra contexto visual (585 px nativos) e custo de processamento. O máximo de 3° fica abaixo do FOV de uma imagem (3,5°) e do limite de 2040 px do cutout.
- **Por que cutout em pixels**: evita que `size × 1.5` em graus ultrapasse o tamanho do detector e garante um limite exato e previsível de memória.
- **Por que Lanczos com alfa pré-multiplicado**: Lanczos preserva nitidez ao ampliar. Sem pré-multiplicação, pixels transparentes (cor preta, alfa 0) "vazam" para as bordas e criam halos escuros.
- **Por que RGB compõe exposições vizinhas**: o SPHEREx tem 6 detectores em pares (D1+D4, D2+D5, D3+D6); cada par vê uma parte **diferente** do campo em cada exposição. Nos dados reais (fixture `sia_m101_qr3.xml`), um ponto fixo do céu é coberto numa observation por um único par (às vezes um só detector), e nenhuma observation tem D1, D2 e D3 juntos no ponto. Exposições consecutivas repetem o mesmo par; os outros pares voltam horas ou dias depois. Por isso cada canal vem da exposição mais próxima no tempo, na mesma visit, que cobre o ponto com aquele detector. Medido em 2026-11-14: M101, M51 e Órion tiveram canais separados por 21 h a 4,8 dias, e algumas visits não têm um dos pares (→ 404, escolher outra observation em `/epochs`). Para o céu estático isso equivale a uma exposição única; objetos que se movem ou variam entre as exposições (asteroides, cometas, estrelas variáveis) podem aparecer com cores separadas, e a área válida é a interseção das coberturas dos canais. A reprojeção para a grade comum absorve as diferenças de apontamento.
- **Por que D3,D2,D1 como padrão**: convenção astronômica (maior comprimento de onda → vermelho) e faixas próximas do infravermelho mais conhecido do público (1–2,4 µm), em que estrelas e poeira se distinguem bem.
- **Por que escala por canal**: os detectores têm níveis de brilho muito diferentes; uma escala única deixaria a imagem dominada por um canal.
- **Por que mediana e subtração de fundo**: a mediana é robusta a raios cósmicos, pixels ruins e objetos transitórios. A subtração de fundo por frame evita que diferenças residuais de luz zodiacal entre exposições criem manchas.
- **Por que `stack=false` por padrão**: o desafio pede mostrar como o céu muda; a mediana apaga objetos em movimento. O empilhamento é um modo "contemplação", não "descoberta".
- **Limitação LVF no stack**: exposições consecutivas de uma visit posicionam o mesmo ponto do céu em regiões diferentes do filtro linear variável. O stack de um detector combina comprimentos de onda dentro da faixa daquele detector. Para visualização isso é aceitável e se aproxima de uma imagem "banda larga".
- **Por que orçamento por requisição**: `rgb + stack + size=3` poderia exigir 24 downloads de ~70 MB, inviável em instâncias pequenas (o backend atual roda no Render). O orçamento degrada com elegância antes de falhar.

## 8. Dependências e integrações externas

### Sistemas externos

- **EXT-001**: IRSA SIA2 — sem mudanças.
- **EXT-002**: IRSA IBE Cutouts — passa a ser chamado com `size={n}pix`. Verificado em 2026-11-14: `pix` retorna 200, enquanto `px` retorna 503 "Server busy".

### Infraestrutura

- **INF-001**: Recomendado ≥ 2 GiB de RAM por instância para `mode=rgb` e `stack=true` com `size ≥ 2`. Em instâncias de 512 MB, reduzir `MAX_CONCURRENT_RENDERS`, `MAX_CUTOUTS_PER_REQUEST` e `MAX_FETCH_PIXELS_PER_REQUEST` via env, sem mudança de código.

### Plataforma

- **PLT-101**: `astropy.stats` (sigma-clipping), já incluído no astropy.
- **PLT-102**: Pillow com suporte aos modos `RGBa` e `Image.Resampling.LANCZOS`.

## 9. Exemplos e casos de borda

### 9.1 Requisições

```bash
# Campo amplo padrão (1°, 585 px)
curl -o wide.png "http://localhost:8000/image?ra=83.82&dec=-5.39&observation_id=<id>&detector=D2"

# Campo amplo ampliado 2× para tela grande (1170 px)
curl -o wide2x.png "http://localhost:8000/image?ra=83.82&dec=-5.39&observation_id=<id>&detector=D2&upscale=2"

# Cor falsa infravermelha padrão (R=D3, G=D2, B=D1)
curl -o rgb.png -D - "http://localhost:8000/image?ra=83.82&dec=-5.39&observation_id=<id>&mode=rgb"

# Cor falsa "infravermelho profundo"
curl -o rgb_deep.png "http://localhost:8000/image?ra=83.82&dec=-5.39&observation_id=<id>&mode=rgb&detectors=D6,D4,D2"

# Modo contemplação: RGB + empilhamento + upscale
curl -o best.png -D - "http://localhost:8000/image?ra=83.82&dec=-5.39&observation_id=<id>&mode=rgb&stack=true&size=1.5&upscale=2"

# Reaproveitar a escala RGB entre datas (copiar valores de X-Scale-Min / X-Scale-Max)
curl -o rgb_b.png "http://localhost:8000/image?ra=83.82&dec=-5.39&observation_id=<outro_id>&mode=rgb&scale_mins=0.1,0.2,0.3&scale_maxs=5,8,12"
```

(`ra=83.82&dec=-5.39` = Nebulosa de Órion. Os `observation_id` devem vir de `/epochs`.)

### 9.2 Casos de borda

| Caso | Comportamento |
|---|---|
| Frames do stack com cobertura parcial diferente | `nanmedian` usa os frames disponíveis por pixel; onde nenhum cobre, NaN → transparente. |
| Frame do stack falha no download (timeout/5xx após retry) | Descartar o frame, logar `warning` e seguir com os restantes. Se for a **âncora** do canal (a referência em `single`), falhar com o erro de upstream correspondente. `X-Stack-Count` reflete os frames efetivamente usados. |
| Referência sem nenhum dos detectores RGB pedidos | Válido: os três canais vêm de outras observations da visit; `X-Observation-Id` continua sendo a referência. |
| Objeto em movimento em `rgb` | Pode aparecer com cores separadas (cada canal é de uma exposição diferente); `X-Channel-Time-Span-Seconds` indica o intervalo. |
| Canal RGB todo NaN | `422 EMPTY_IMAGE`, com `details.empty_channels`. |
| `upscale=1` | Nenhum redimensionamento (não chamar o Pillow resize). |
| `size` pequeno com `upscale=4` (ex.: 0.05° → 29 px → 116 px) | Válido. |
| `scale_mins` com valores não numéricos | `422 VALIDATION_ERROR`. |
| `detectors` com espaços (`D3, D2, D1`) | Aceitar, removendo espaços. |
| Minúsculas (`d2`) | `422` (enum estrito, igual à spec base). |

## 10. Critérios de validação

- **VAL-101**: AC-101 a AC-107 passam antes de iniciar a Fase B.
- **VAL-102**: AC-201 a AC-207 e AC-301 a AC-309 passam ao final da Fase B.
- **VAL-103**: Todos os critérios da spec base continuam passando, ajustando apenas os testes que dependiam do default antigo de `size` (0.25 → 1.0).
- **VAL-104**: `/openapi.json` documenta todos os novos parâmetros, headers e erros, incluindo as notas de REQ-206 (colormap ignorado em rgb) e REQ-306 (stack apaga objetos móveis), e a premissa física da seção 1.
- **VAL-105**: Grep no código não encontra dependências de IA/super-resolução nem de SDKs de nuvem.
- **VAL-106**: (Live) Inspeção visual de M101 e Órion em `mode=rgb&stack=true`: cores coerentes (estrelas não ficam todas de uma única cor), sem faixas, sem halos nas bordas transparentes, norte para cima.
- **VAL-107**: README atualizado com: nova tabela de parâmetros, explicação curta da resolução do SPHEREx, recomendações de RAM (GUD-104) e exemplos da seção 9.1.

## 11. Especificações relacionadas / leitura complementar

- `spec/spec-tool-spherex-image-api.md` — spec base (v1).
- Planejada: `spec/spec-infrastructure-spherex-image-cache.md` — cache (a chave de cache deve incluir todos os parâmetros desta spec, incluindo `mode`, `detectors`, `stack` e `upscale`).
- SPHEREx Data Products (IRSA): https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products
- IRSA Image Server Cutouts: https://irsa.ipac.caltech.edu/ibe/cutouts.html
- Astropy — sigma clipping: https://docs.astropy.org/en/stable/stats/robust.html
- Pillow — Image.resize: https://pillow.readthedocs.io/en/stable/reference/Image.html
