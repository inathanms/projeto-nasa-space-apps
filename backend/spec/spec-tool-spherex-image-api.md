---
title: SPHEREye — Image API (v0.1: /epochs e /image, sem cache)
version: 0.1
date_created: 2026-11-14
last_updated: 2026-11-14
owner: Time do hackathon NASA (backend)
tags: [tool, api, python, fastapi, astronomy, spherex, irsa]
---

# Introdução

Esta especificação define a primeira versão da API backend do **SPHEREye**, uma aplicação web pública que permite a qualquer pessoa escolher um ponto do céu e um momento no tempo e ver a imagem que o telescópio SPHEREx (NASA) registrou ali, comparando como o céu muda entre visitas.

A API é um serviço HTTP stateless em Python que:

1. consulta o arquivo público da NASA/IPAC (IRSA) para descobrir **quando** o SPHEREx observou uma posição (`GET /epochs`);
2. baixa um recorte da imagem científica (FITS), processa e devolve um **PNG pronto para exibição** (`GET /image`).

Esta versão **não implementa cache**. O cache será adicionado em uma especificação posterior, e o design deve permitir isso sem refatoração (ver PAT-003).

## 1. Propósito e escopo

**Propósito:** guiar um agente de implementação (IA) na construção do backend, do zero até um container executável, com OpenAPI em `/docs`.

**Dentro do escopo:**

- Rotas `GET /epochs`, `GET /image` e `GET /health`.
- Cliente HTTP para o serviço SIA2 do IRSA e para o serviço de cutouts do IRSA.
- Pipeline de processamento de imagem (FITS → PNG).
- Configuração por variáveis de ambiente, Dockerfile, testes automatizados, README.

**Fora do escopo (não implementar):**

- Cache (memória, Redis, GCS, R2 ou outro).
- Rota de footprints, autenticação, rate limiting, banco de dados, filas, jobs de pré-renderização.
- SDKs ou integrações específicas de provedores de nuvem (GCP, Azure, AWS, Render).
- Frontend (fica em `frontend/`, outro escopo).

**Público-alvo:** agente de implementação e desenvolvedores do time.

**Premissas:**

- O repositório é um monorepo com `frontend/` (Next.js) e `backend/` (esta API) na raiz.
- O frontend consome a API via HTTP a partir do navegador (CORS necessário).
- A API pode ser hospedada em Google Cloud Run, Azure Container Apps, Render ou localmente via Docker, sem alteração de código.

## 2. Definições

| Termo | Definição |
|---|---|
| **SPHEREx** | Missão da NASA lançada em março de 2025 que mapeia o céu inteiro a cada ~6 meses em 102 faixas do infravermelho próximo (0,75–5,0 µm). |
| **IRSA** | NASA/IPAC Infrared Science Archive. Hospeda os dados públicos do SPHEREx. |
| **SIA2** | Simple Image Access Protocol v2 (padrão IVOA). Endpoint de busca: dado um ponto do céu, devolve uma tabela com as imagens que o cobrem. |
| **VOTable** | Formato XML padrão IVOA para tabelas astronômicas. Formato de resposta padrão do SIA2. |
| **FITS** | Flexible Image Transport System. Formato binário de imagens científicas. |
| **MEF** | Multi-Extension FITS. Arquivo FITS com várias HDUs. |
| **HDU** | Header Data Unit. Cada "extensão" de um FITS (cabeçalho + dados). Identificada pelo cabeçalho `EXTNAME`. |
| **Cutout** | Recorte espacial de um MEF feito pelo próprio servidor do IRSA. |
| **RA / Dec** | Ascensão reta e declinação. Coordenadas celestes equatoriais (ICRS/J2000), em graus. RA ∈ [0, 360), Dec ∈ [-90, 90]. |
| **MJD** | Modified Julian Date. Dias desde 1858-11-17 00:00 UTC. Ex.: MJD 61177.457 ≈ 2026-05-17T10:58Z. |
| **Detector (D1–D6)** | O SPHEREx tem 6 detectores; cada apontamento gera 6 imagens simultâneas, uma por detector, cada uma cobrindo uma faixa de comprimento de onda. |
| **Observation** | Uma exposição do telescópio, identificada por `obs_id` no IRSA (ex.: `2026W20_2A_0464_3`). Agrupa até 6 imagens (uma por detector). |
| **Visit** | Conjunto de observations da mesma região feitas em sequência curta (minutos/horas). Visitas consecutivas da mesma região são separadas por meses. É a unidade natural do slider de tempo do frontend. |
| **ZODI** | Extensão do MEF com o modelo da luz zodiacal (brilho difuso do Sistema Solar), que deve ser subtraída para melhorar o contraste. |
| **FLAGS** | Extensão do MEF com uma máscara de bits por pixel indicando problemas (pixel quente, morto, saturado etc.). |
| **WCS** | World Coordinate System. Metadados do cabeçalho FITS que mapeiam pixel ↔ coordenada celeste. |
| **Reprojeção** | Reamostrar uma imagem para outra grade WCS. Aqui: grade fixa "norte para cima" centrada no ponto pedido. |
| **Stretch** | Função não linear aplicada aos valores de brilho para tornar visíveis objetos fracos (asinh, log, sqrt, linear). |
| **MJy/sr** | Megajansky por esterradiano. Unidade de brilho de superfície dos pixels do SPHEREx. |
| **LVF** | Linear Variable Filter. O filtro do SPHEREx varia de comprimento de onda ao longo do detector. |

## 3. Requisitos, restrições e diretrizes

### 3.1 Requisitos funcionais

- **REQ-001**: A API deve expor `GET /epochs`, que recebe uma posição (RA/Dec) e devolve todas as observations do SPHEREx que cobrem essa posição, ordenadas por tempo e agrupadas em visits (contrato na seção 4.2).
- **REQ-002**: A API deve expor `GET /image`, que recebe posição, `observation_id` e `detector` e devolve uma imagem PNG processada daquela região (contrato na seção 4.3).
- **REQ-003**: A API deve expor `GET /health`, que devolve `200` com `{"status": "ok", "version": "<versão>"}` **sem** chamar o IRSA.
- **REQ-004**: A documentação OpenAPI interativa (Swagger UI) deve estar em `/docs` e o schema JSON em `/openapi.json`. Toda rota, parâmetro e resposta (incluindo erros) deve ter descrição e exemplo.
- **REQ-005**: Todos os nomes de rotas, parâmetros de query, campos JSON, headers customizados e códigos de erro devem estar em inglês, em `snake_case` (parâmetros e campos) ou `UPPER_SNAKE_CASE` (códigos de erro).
- **REQ-006**: `GET /epochs` deve aceitar filtro opcional de intervalo de tempo (`start_time`, `end_time`, ISO 8601) e de detector.
- **REQ-007**: `GET /image` deve, por padrão (`align=true`), reprojetar a imagem para uma grade fixa norte-para-cima, leste-para-a-esquerda, centrada exatamente em (`ra`, `dec`), com escala de pixel nativa do SPHEREx (6,15″/px). Assim, imagens de datas diferentes ficam pixel a pixel alinhadas e podem ser comparadas (efeito "blink").
- **REQ-008**: `GET /image` deve devolver nos headers HTTP os limites de escala usados (`X-Scale-Min`, `X-Scale-Max`, em MJy/sr) e aceitar `scale_min`/`scale_max` como entrada. Assim, o frontend pode reaplicar a escala da primeira imagem nas demais e evitar "piscar" de brilho entre datas.
- **REQ-009**: Pixels inválidos (mascarados ou fora da área coberta pela imagem) devem ser transparentes no PNG (canal alfa = 0).
- **REQ-010**: A API deve usar `spherex_qr3` como coleção padrão, configurável por variável de ambiente, e aceitar o parâmetro `collection` restrito a uma lista permitida (seção 4.1).

### 3.2 Restrições

- **CON-001**: Linguagem Python ≥ 3.12. Framework FastAPI. Servidor ASGI Uvicorn.
- **CON-002**: Nenhuma dependência de SDK de provedor de nuvem (`google-cloud-*`, `azure-*`, `boto3` etc.) nesta versão.
- **CON-003**: Toda configuração deve vir de variáveis de ambiente (seção 4.5). Nenhum valor de ambiente pode estar hardcoded no código além dos defaults documentados.
- **CON-004**: A aplicação deve escutar em `0.0.0.0` na porta definida pela variável `PORT` (Cloud Run e Render injetam `PORT`). Default: `8000`.
- **CON-005**: A aplicação deve ser stateless: não pode gravar arquivos em disco além de temporários em memória; nenhum estado compartilhado entre requisições além de clientes HTTP reutilizáveis e o semáforo de concorrência.
- **CON-006**: Logs somente em stdout/stderr, em JSON de uma linha por evento.
- **CON-007**: Nunca baixar o MEF completo (~70 MB). Sempre usar o serviço de cutout do IRSA.
- **CON-008**: Não usar `matplotlib.pyplot` (não é thread-safe). Usar apenas `matplotlib.colormaps` para lookup de colormap.
- **CON-009**: Todo o código fica em `backend/`. Nenhum arquivo fora de `backend/` deve ser criado ou alterado, exceto este documento em `spec/`.
- **CON-010**: Colunas do SIA2 devem ser lidas **pelo nome**, nunca pela posição.
- **CON-011**: HDUs do FITS devem ser localizadas **pelo `EXTNAME`** (`IMAGE`, `FLAGS`, `ZODI`), nunca pelo índice.

### 3.3 Segurança

- **SEC-001**: A API só pode fazer requisições de saída para hosts sob `irsa.ipac.caltech.edu`. Uma `access_url` vinda do SIA com outro host deve ser rejeitada com erro `502 UPSTREAM_INVALID_RESPONSE` (prevenção de SSRF).
- **SEC-002**: O usuário nunca fornece URLs. O `access_url` é sempre obtido da resposta do SIA, a partir de `observation_id` + `detector`.
- **SEC-003**: Todos os parâmetros de entrada devem ser validados (tipo, faixa, enum) antes de qualquer chamada externa. Parâmetros desconhecidos são ignorados.
- **SEC-004**: CORS configurável por `CORS_ALLOWED_ORIGINS`. Métodos permitidos: `GET` e `OPTIONS`. Headers customizados de `/image` devem ser listados em `expose_headers`.
- **SEC-005**: Tamanho máximo de download de um cutout: `IRSA_MAX_CUTOUT_BYTES` (default 50 MB). Ultrapassar → `502 UPSTREAM_INVALID_RESPONSE`. Ler a resposta em streaming e abortar ao ultrapassar.
- **SEC-006**: Mensagens de erro não podem expor stack traces, caminhos internos ou URLs completas do upstream.
- **SEC-007**: O container deve rodar como usuário não-root.

### 3.4 Desempenho e confiabilidade

- **PER-001**: Processamento de imagem (CPU-bound) deve rodar fora do event loop (rota síncrona `def` do FastAPI ou `run_in_threadpool`).
- **PER-002**: Limitar renderizações simultâneas por processo com um semáforo de tamanho `MAX_CONCURRENT_RENDERS` (default 4). Requisições excedentes aguardam até `RENDER_QUEUE_TIMEOUT_SECONDS` (default 30) e depois falham com `503 SERVER_BUSY`.
- **PER-003**: Timeouts de upstream configuráveis: SIA (default 30 s), cutout (default 60 s).
- **PER-004**: Em timeout ou resposta 5xx do IRSA, fazer até `IRSA_MAX_RETRIES` (default 1) novas tentativas, com backoff de 1 s. Não repetir em 4xx.
- **PER-005**: Reutilizar um único cliente `httpx` por processo (connection pooling), criado no lifespan da aplicação.
- **PER-006**: Meta: `/epochs` < 5 s e `/image` (tamanho padrão) < 10 s em p95, excluindo lentidão do IRSA.

### 3.5 Diretrizes e padrões

- **GUD-001**: Seguir PEP 8; lint e formatação com `ruff`; type hints em todas as funções públicas.
- **GUD-002**: Dependências gerenciadas com `uv` (`pyproject.toml` + `uv.lock`).
- **GUD-003**: Docstrings curtas nas funções públicas, explicando unidades (graus, MJD, metros, µm, MJy/sr).
- **PAT-001**: Separação em camadas: `api` (rotas, schemas, erros HTTP) → `services` (orquestração) → `clients` (I/O com IRSA) → `processing` (funções puras numpy/astropy, sem I/O).
- **PAT-002**: Funções de `processing` devem ser puras e testáveis com arrays sintéticos, sem rede.
- **PAT-003**: O acesso ao IRSA deve passar por interfaces (`typing.Protocol`), por exemplo `SiaClient.search(...)` e `CutoutClient.fetch(...)`. O cache futuro será um decorator/wrapper dessas interfaces, sem mudar `services`.
- **PAT-004**: Injeção de dependência via `Depends` do FastAPI para settings e clientes, permitindo substituí-los nos testes.
- **PAT-005**: Erros de domínio são exceções tipadas (`ObservationNotFoundError`, `UpstreamTimeoutError` etc.) convertidas para HTTP em um único exception handler.

## 4. Interfaces e contratos de dados

### 4.1 Tipos compartilhados

| Nome | Tipo | Regra |
|---|---|---|
| `ra` | float | `0 <= ra < 360`, graus ICRS. Valores fora da faixa → 422. |
| `dec` | float | `-90 <= dec <= 90`, graus ICRS. |
| `detector` | enum string | `D1`, `D2`, `D3`, `D4`, `D5`, `D6`. |
| `collection` | enum string | `spherex_qr3`, `spherex_qr3_deep`, `spherex_dr1`, `spherex_dr1_deep`. Default: `IRSA_DEFAULT_COLLECTION`. |
| timestamps | string | ISO 8601 UTC com sufixo `Z`, precisão de segundos. Ex.: `2026-05-17T10:58:03Z`. |

Faixas de comprimento de onda nominais por detector (referência para documentação; os valores reais vêm do SIA):

| Detector | λ (µm) |
|---|---|
| D1 | 0,75 – 1,09 |
| D2 | 1,10 – 1,62 |
| D3 | 1,63 – 2,41 |
| D4 | 2,42 – 3,82 |
| D5 | 3,83 – 4,41 |
| D6 | 4,42 – 5,00 |

### 4.2 `GET /epochs`

Lista as observations do SPHEREx que cobrem uma posição do céu.

**Query params**

| Param | Tipo | Obrigatório | Default | Regra |
|---|---|---|---|---|
| `ra` | float | sim | — | ver 4.1 |
| `dec` | float | sim | — | ver 4.1 |
| `radius` | float (graus) | não | `0.001` | `0 < radius <= 1.0` |
| `collection` | enum | não | env | ver 4.1 |
| `detector` | enum | não | todos | Se informado, só devolve imagens desse detector e só as observations que o possuem. |
| `start_time` | ISO 8601 | não | — | Limite inferior (inclusivo). |
| `end_time` | ISO 8601 | não | — | Limite superior (inclusivo). Se ambos informados, `start_time <= end_time`, senão 422. |

**Comportamento**

1. Montar a requisição SIA2: `GET {IRSA_SIA_URL}?COLLECTION={collection}&POS=CIRCLE {ra} {dec} {radius}&MAXREC={IRSA_SIA_MAXREC}`. Sem `RESPONSEFORMAT` (VOTable padrão). Se houver filtro de tempo, adicionar `TIME={mjd_start} {mjd_end}`, usando `-inf`/`+inf` para o limite ausente. Codificar os parâmetros com o encoder do `httpx` (não montar strings manualmente).
2. Parsear o VOTable com `astropy.io.votable.parse_single_table` (ou equivalente) e ler as colunas pelo nome: `obs_id`, `energy_bandpassname`, `em_min`, `em_max`, `t_min`, `t_max`, `t_exptime`, `s_ra`, `s_dec`, `s_region`, `access_url`, `dataproduct_subtype`.
3. Descartar linhas cujo `dataproduct_subtype` não seja `science`.
4. Extrair o detector de `energy_bandpassname` (`SPHEREx-D2` → `D2`). Linhas com valor fora do padrão `SPHEREx-D[1-6]` são descartadas e logadas como `warning`.
5. Converter `em_min`/`em_max` de metros para µm (×1e6, arredondar para 4 casas).
6. Converter `t_min`/`t_max` (MJD) para ISO 8601 UTC com `astropy.time.Time(..., format="mjd", scale="utc")`.
7. Parsear `s_region` (`POLYGON ICRS ra1 dec1 ra2 dec2 ...`) em uma lista de pares `[ra, dec]`, removendo o último ponto se for igual ao primeiro.
8. Agrupar as linhas por `obs_id` em observations. `start_mjd` = menor `t_min`, `end_mjd` = maior `t_max` do grupo.
9. Ordenar as observations por `start_mjd` crescente.
10. Agrupar em visits: percorrer em ordem; uma nova visit começa quando `start_mjd` da observation atual − `end_mjd` da anterior > `VISIT_GAP_DAYS` (default 2.0). `visit_index` começa em 0.
10a. Em cada visit, `detectors` é a união ordenada (D1..D6) dos detectores das imagens de todas as suas observations (respeita o filtro `detector`); `rgb_available` é `true` se `detectors` contém D1, D2 e D3 (o `mode=rgb` padrão de `/image` funciona com qualquer observation da visit). Com filtro `detector`, é `false` por construção.
11. Se o VOTable indicar truncamento (`INFO name="QUERY_STATUS" value="OVERFLOW"`), definir `truncated: true`.
12. Resultado vazio não é erro: retornar `200` com listas vazias.

**Resposta 200** (`application/json`)

```json
{
  "query": {
    "ra": 210.80227,
    "dec": 54.34895,
    "radius": 0.001,
    "collection": "spherex_qr3",
    "detector": null,
    "start_time": null,
    "end_time": null
  },
  "total_observations": 2,
  "total_visits": 1,
  "truncated": false,
  "visits": [
    {
      "visit_index": 0,
      "start_time": "2026-05-17T10:53:45Z",
      "end_time": "2026-05-17T10:59:58Z",
      "start_mjd": 61177.453996,
      "end_mjd": 61177.458313,
      "observation_ids": ["2026W20_2A_0464_1", "2026W20_2A_0464_3"],
      "detectors": ["D1", "D2", "D3", "D4", "D5", "D6"],
      "rgb_available": true
    }
  ],
  "observations": [
    {
      "observation_id": "2026W20_2A_0464_1",
      "visit_index": 0,
      "start_time": "2026-05-17T10:53:45Z",
      "end_time": "2026-05-17T10:55:41Z",
      "start_mjd": 61177.453996,
      "end_mjd": 61177.455328,
      "exposure_seconds": 113.58,
      "detectors": [
        {
          "detector": "D2",
          "wavelength_min_um": 1.1033,
          "wavelength_max_um": 1.6499,
          "image_center": { "ra": 212.450503, "dec": 52.949064 },
          "footprint": [
            [212.227543, 55.391716],
            [216.510588, 53.000415],
            [212.633564, 50.474454],
            [208.363692, 52.745649]
          ]
        }
      ]
    }
  ]
}
```

Regras: `detectors` ordenado de D1 a D6; `observation_ids` em ordem temporal; floats de coordenadas com 6 casas decimais.

### 4.3 `GET /image`

Devolve um PNG processado de uma região de uma imagem do SPHEREx.

**Query params**

| Param | Tipo | Obrigatório | Default | Regra |
|---|---|---|---|---|
| `ra` | float | sim | — | Centro da imagem de saída. |
| `dec` | float | sim | — | Centro da imagem de saída. |
| `observation_id` | string | sim | — | Regex `^[A-Za-z0-9_]{1,64}$`. Valor vindo de `/epochs`. |
| `detector` | enum | sim | — | `D1`–`D6`. |
| `collection` | enum | não | env | ver 4.1 |
| `size` | float (graus) | não | `0.25` | `0.01 <= size <= 1.0`. Lado do quadrado de saída. |
| `align` | bool | não | `true` | `true`: reprojeta para grade norte-para-cima centrada em (ra, dec). `false`: orientação nativa do detector. |
| `subtract_zodi` | bool | não | `true` | Subtrair a extensão `ZODI`. |
| `stretch` | enum | não | `asinh` | `asinh`, `linear`, `log`, `sqrt`. |
| `colormap` | enum | não | `inferno` | `gray`, `inferno`, `magma`, `viridis`, `plasma`, `cividis`. |
| `percentile_low` | float | não | `1.0` | `0 <= x < percentile_high` |
| `percentile_high` | float | não | `99.5` | `percentile_low < x <= 100` |
| `scale_min` | float (MJy/sr) | não | — | Se informado, `scale_max` também é obrigatório, e `scale_min < scale_max`. Sobrepõe os percentis. |
| `scale_max` | float (MJy/sr) | não | — | idem |

**Comportamento (pipeline)**

1. **Validar** todos os parâmetros (422 em caso de erro).
2. **Resolver a imagem**: chamar o SIA (`POS=CIRCLE {ra} {dec} 0.001`, `collection`) e buscar a linha com `obs_id == observation_id` e detector == `detector`. Se não existir → `404 OBSERVATION_NOT_FOUND`. Isso cobre ids inexistentes e posições fora da área daquela observation.
3. **Validar host** do `access_url` (SEC-001).
4. **Pedir o cutout**: `GET {access_url}?center={ra},{dec}&size={fetch_size}`, com `fetch_size = min(size * 1.5, 2.0)` em graus quando `align=true` (margem para a rotação da reprojeção não deixar cantos vazios) e `fetch_size = size` quando `align=false`. Seguir redirects. Se o corpo começar com os bytes gzip `1f 8b`, descomprimir. O corpo deve começar com `SIMPLE`, senão `502 UPSTREAM_INVALID_RESPONSE`.
5. **Abrir o MEF** em memória (`astropy.io.fits.open(io.BytesIO(data))`). Localizar as HDUs `IMAGE` (obrigatória, senão 502), `FLAGS` e `ZODI` (opcionais; se faltarem, pular o passo correspondente e logar `warning`).
6. **Converter** `IMAGE` para `float32`. Se `subtract_zodi` e `ZODI` existir: `data = image - zodi`.
7. **Mascarar** pixels ruins usando `FLAGS` (ver 4.3.1): `data[mask] = NaN`.
8. **Geometria**:
   - `align=true`: construir o WCS de destino: projeção `TAN`, `CRVAL = (ra, dec)`, `CDELT1 = -6.15/3600`, `CDELT2 = +6.15/3600` (graus/px; leste à esquerda, norte em cima), `NAXIS1 = NAXIS2 = n = round(size * 3600 / 6.15)` (mínimo 16 px), `CRPIX` no centro (`(n + 1) / 2`). Reprojetar com `reproject.reproject_interp(order="bilinear")` usando o WCS **celestial** do header da HDU `IMAGE` (`WCS(header).celestial`). Pixels fora da imagem de origem viram NaN.
   - `align=false`: usar o cutout como veio.
   - Em ambos os casos, inverter verticalmente o array antes de gerar o PNG (no FITS a linha 0 é a de baixo; no PNG, a de cima).
9. **Escala**: se `scale_min`/`scale_max` informados, usá-los. Senão, calcular `vmin`/`vmax` com `numpy.nanpercentile` nos pixels finitos usando `percentile_low`/`percentile_high`. Se não houver pixel finito → `422 EMPTY_IMAGE`. Se `vmin == vmax`, usar `vmax = vmin + 1e-6`.
10. **Normalizar e aplicar stretch**: `x = clip((data - vmin) / (vmax - vmin), 0, 1)`. Aplicar o stretch com `astropy.visualization` (`AsinhStretch(a=0.1)`, `LinearStretch()`, `LogStretch(a=1000)`, `SqrtStretch()`).
11. **Colormap**: `rgba = matplotlib.colormaps[colormap](x, bytes=True)` (uint8 H×W×4). Definir `rgba[..., 3] = 0` onde `data` é NaN.
12. **Codificar PNG** com Pillow (`mode="RGBA"`, `optimize=False`).
13. **Responder** com o PNG e os headers da tabela abaixo.

#### 4.3.1 Máscara de FLAGS

O cabeçalho da HDU `FLAGS` do SPHEREx define o significado de cada bit com palavras-chave no formato `MP_<NOME> = <bit>` (ex.: `MP_HOT = 10`). Implementação obrigatória:

1. Ler todas as palavras-chave do header de `FLAGS` que começam com `MP_` e montar o dicionário `{nome: bit}`.
2. Rejeitar (mascarar) os pixels que tenham qualquer bit cujo nome esteja em `FLAGS_REJECT_NAMES` (env, default: `NONFUNC,MISSING_DATA,HOT,COLD,OVERFLOW,SUR_ERROR,PHANMISS`).
3. **Nunca** mascarar o bit `SOURCE` (ele indica presença de fonte astronômica — estrelas — e mascará-lo apagaria os próprios objetos de interesse).
4. Se o header não tiver nenhuma palavra-chave `MP_*`, não mascarar nada e logar `warning` com `event="flags_definitions_missing"`.
5. Nomes de `FLAGS_REJECT_NAMES` que não existirem no header são ignorados silenciosamente.

> Nota para o agente: a convenção `MP_*` e os nomes de bits acima devem ser **confirmados** inspecionando o header de um cutout real na primeira execução (ver VAL-008). Se a convenção for outra, adaptar a leitura mantendo as regras 2 a 5.

**Resposta 200** — `Content-Type: image/png`

| Header | Exemplo | Descrição |
|---|---|---|
| `X-Observation-Id` | `2026W20_2A_0464_3` | |
| `X-Detector` | `D2` | |
| `X-Observation-Time` | `2026-05-17T10:58:03Z` | `t_min` da imagem em ISO 8601. |
| `X-Wavelength-Min-Um` | `1.1033` | |
| `X-Wavelength-Max-Um` | `1.6499` | |
| `X-Scale-Min` | `0.0123` | `vmin` usado, MJy/sr. |
| `X-Scale-Max` | `4.5678` | `vmax` usado, MJy/sr. |
| `X-Image-Width` / `X-Image-Height` | `146` | Pixels. |
| `X-Pixel-Scale-Arcsec` | `6.15` | |
| `X-Valid-Pixel-Fraction` | `0.982` | Fração de pixels não transparentes. |
| `Cache-Control` | `public, max-age=86400` | Imagens de arquivo não mudam. Isso já ajuda caches de navegador/CDN na v1. |

O OpenAPI deve declarar `responses={200: {"content": {"image/png": {}}, "description": ...}}` e documentar esses headers.

### 4.4 Erros

Todas as respostas de erro usam `Content-Type: application/json` e este formato:

```json
{
  "error": {
    "code": "OBSERVATION_NOT_FOUND",
    "message": "No image found for observation_id=2026W20_2A_0464_9 detector=D2 at the requested position.",
    "details": {}
  }
}
```

| HTTP | `code` | Quando |
|---|---|---|
| 422 | `VALIDATION_ERROR` | Parâmetro ausente, tipo errado, fora da faixa, combinação inválida. `details` contém a lista de campos. O formato padrão do FastAPI deve ser substituído por este. |
| 404 | `OBSERVATION_NOT_FOUND` | `/image`: combinação observation_id + detector + posição não encontrada. |
| 422 | `EMPTY_IMAGE` | `/image`: nenhum pixel válido após máscara/reprojeção. |
| 502 | `UPSTREAM_ERROR` | IRSA respondeu 4xx/5xx (após retries). |
| 502 | `UPSTREAM_INVALID_RESPONSE` | VOTable inválido, FITS inválido, HDU `IMAGE` ausente, host não permitido, cutout grande demais. |
| 504 | `UPSTREAM_TIMEOUT` | Timeout do IRSA (após retries). |
| 503 | `SERVER_BUSY` | Semáforo de renderização esgotado (PER-002). |
| 500 | `INTERNAL_ERROR` | Qualquer outra exceção. Logar com stack trace; não expor ao cliente. |

### 4.5 Configuração (variáveis de ambiente)

Carregar com `pydantic-settings`. Fornecer `backend/.env.example` com todas elas.

| Variável | Default | Descrição |
|---|---|---|
| `PORT` | `8000` | Porta HTTP. |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warning`, `error`. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Lista separada por vírgula. `*` permitido. |
| `IRSA_SIA_URL` | `https://irsa.ipac.caltech.edu/SIA` | |
| `IRSA_ALLOWED_HOST` | `irsa.ipac.caltech.edu` | SEC-001. |
| `IRSA_DEFAULT_COLLECTION` | `spherex_qr3` | |
| `IRSA_SIA_MAXREC` | `5000` | |
| `IRSA_SIA_TIMEOUT_SECONDS` | `30` | |
| `IRSA_CUTOUT_TIMEOUT_SECONDS` | `60` | |
| `IRSA_MAX_RETRIES` | `1` | |
| `IRSA_MAX_CUTOUT_BYTES` | `52428800` | 50 MB. |
| `HTTP_USER_AGENT` | `sphereye/0.1 (+hackathon)` | Enviado em toda chamada ao IRSA. |
| `MAX_CONCURRENT_RENDERS` | `4` | PER-002. |
| `RENDER_QUEUE_TIMEOUT_SECONDS` | `30` | PER-002. |
| `VISIT_GAP_DAYS` | `2.0` | Agrupamento de visits. |
| `FLAGS_REJECT_NAMES` | `NONFUNC,MISSING_DATA,HOT,COLD,OVERFLOW,SUR_ERROR,PHANMISS` | 4.3.1. |
| `APP_VERSION` | `0.1.0` | Exposto em `/health` e no OpenAPI. |

### 4.6 Estrutura de diretórios

```
backend/
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── .dockerignore
├── .env.example
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py              # create_app(): FastAPI, lifespan (httpx client), CORS, exception handlers, routers
│   ├── config.py            # Settings (pydantic-settings)
│   ├── logging.py           # logging JSON em stdout
│   ├── api/
│   │   ├── deps.py          # Depends: settings, clients, services
│   │   ├── errors.py        # exception handlers → formato 4.4
│   │   ├── schemas.py       # modelos Pydantic de request/response
│   │   └── routes/
│   │       ├── health.py
│   │       ├── epochs.py
│   │       └── image.py
│   ├── domain/
│   │   ├── models.py        # dataclasses: ImageRecord, Observation, Visit, Detector (enum)
│   │   └── errors.py        # exceções de domínio
│   ├── clients/
│   │   ├── protocols.py     # SiaClient, CutoutClient (typing.Protocol) — PAT-003
│   │   ├── irsa_sia.py      # implementação HTTP + parse VOTable → list[ImageRecord]
│   │   └── irsa_cutout.py   # implementação HTTP do cutout → bytes
│   ├── services/
│   │   ├── epochs_service.py  # agrupamento observations/visits
│   │   └── image_service.py   # resolve imagem, busca cutout, chama processing
│   └── processing/
│       ├── fits_reader.py   # abre MEF, localiza HDUs por EXTNAME
│       ├── flags.py         # máscara 4.3.1
│       ├── reprojection.py  # WCS de destino + reproject
│       ├── rendering.py     # escala, stretch, colormap, PNG
│       └── timeutils.py     # MJD ↔ ISO
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── sia_m101_qr3.xml       # VOTable real gravado (ver 6)
    │   ├── sia_empty.xml
    │   └── sia_overflow.xml
    ├── unit/
    ├── integration/
    └── live/                       # marcados @pytest.mark.live, desligados por padrão
```

### 4.7 Execução e container

- Comando local: `uv run uvicorn app.main:app --reload --port 8000`.
- `Dockerfile`: base `python:3.12-slim`, instalar dependências com `uv sync --frozen --no-dev`, usuário não-root, `EXPOSE 8000`, e
  `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --proxy-headers --forwarded-allow-ips='*'"]`.
- Sem `HEALTHCHECK` específico de plataforma; `GET /health` atende Cloud Run, Render e Container Apps.
- O README deve conter: como rodar local (uv e Docker), variáveis de ambiente, exemplos `curl` das três rotas e uma seção "Deploy" genérica (build da imagem + variável `PORT`), sem comandos específicos de provedor.

## 5. Critérios de aceitação

- **AC-001**: Dado o servidor rodando, quando acesso `GET /docs`, então vejo o Swagger UI listando `/health`, `/epochs` e `/image` com descrições e exemplos; e `GET /openapi.json` retorna um schema OpenAPI 3.x válido.
- **AC-002**: Quando chamo `GET /health`, então recebo `200 {"status":"ok","version":"0.1.0"}` mesmo com o IRSA inacessível.
- **AC-003**: Dado o fixture `sia_m101_qr3.xml`, quando chamo `GET /epochs?ra=210.80227&dec=54.34895`, então recebo `200` com observations agrupadas por `obs_id`, ordenadas por `start_mjd`, com detectores `D1`–`D6` ordenados, comprimentos de onda em µm e visits separadas por mais de `VISIT_GAP_DAYS`.
- **AC-004**: Dado `detector=D2`, quando chamo `/epochs`, então nenhum item de `detectors` tem detector diferente de `D2` e observations sem D2 não aparecem.
- **AC-005**: Dado `start_time=2026-05-01T00:00:00Z&end_time=2026-05-31T23:59:59Z`, quando chamo `/epochs`, então a requisição SIA contém `TIME` com os MJDs correspondentes (±1e-6).
- **AC-006**: Dado o fixture `sia_empty.xml`, quando chamo `/epochs`, então recebo `200` com `observations: []`, `visits: []`, `total_observations: 0`.
- **AC-007**: Dado `ra=400` ou `dec=-91` ou `start_time > end_time` ou apenas `scale_min` sem `scale_max`, quando chamo a rota, então recebo `422` com `error.code = "VALIDATION_ERROR"` no formato 4.4.
- **AC-008**: Dado um cutout FITS sintético válido (seção 6), quando chamo `/image` com `align=true` e `size=0.25`, então recebo `200 image/png` RGBA de 146×146 px e todos os headers da seção 4.3.
- **AC-009**: Dada uma estrela sintética a +N px ao norte do centro, quando renderizo com `align=true`, então ela aparece acima do centro no PNG, independentemente da rotação do WCS de origem (testar com rotações de 0°, 37° e 180°).
- **AC-010**: Dados pixels com bits `HOT` e `SOURCE` no FLAGS sintético, quando renderizo, então os pixels `HOT` são transparentes e os pixels apenas `SOURCE` são opacos.
- **AC-011**: Dados `scale_min=0` e `scale_max=10`, quando renderizo, então `X-Scale-Min: 0.0` e `X-Scale-Max: 10.0`, e um pixel de valor 10 tem o valor máximo do colormap.
- **AC-012**: Dado um `observation_id` que não está na resposta do SIA, quando chamo `/image`, então recebo `404 OBSERVATION_NOT_FOUND` e nenhuma chamada de cutout é feita.
- **AC-013**: Dado um `access_url` com host diferente de `irsa.ipac.caltech.edu`, quando chamo `/image`, então recebo `502 UPSTREAM_INVALID_RESPONSE` e nenhuma requisição é feita a esse host.
- **AC-014**: Dado um IRSA que responde 503 duas vezes, quando chamo qualquer rota com `IRSA_MAX_RETRIES=1`, então são feitas exatamente 2 tentativas e recebo `502 UPSTREAM_ERROR`.
- **AC-015**: Dado um IRSA que excede o timeout, então recebo `504 UPSTREAM_TIMEOUT`.
- **AC-016**: Dado `MAX_CONCURRENT_RENDERS=1` e `RENDER_QUEUE_TIMEOUT_SECONDS=0.1`, quando disparo 2 renderizações lentas simultâneas, então uma delas recebe `503 SERVER_BUSY`.
- **AC-017**: Dado um navegador em `http://localhost:3000`, quando ele chama `/image`, então a resposta tem `Access-Control-Allow-Origin` e `Access-Control-Expose-Headers` incluindo `X-Scale-Min` e `X-Scale-Max`.
- **AC-018**: Quando executo `docker build` e `docker run -e PORT=9000 -p 9000:9000`, então `GET http://localhost:9000/health` retorna 200.
- **AC-019**: O código não importa nenhum pacote `google`, `azure`, `boto3` ou `botocore` (verificável por grep).

## 6. Estratégia de testes automatizados

- **Níveis**:
  - *Unit*: `processing/*` (arrays e FITS sintéticos em memória), `timeutils`, parser de `s_region`, agrupamento de visits, parser de VOTable a partir dos fixtures.
  - *Integration*: rotas via `httpx.AsyncClient` + `ASGITransport` (ou `TestClient`), com IRSA mockado por `respx`. Os clientes do IRSA também podem ser substituídos por fakes via `app.dependency_overrides` (PAT-004).
  - *Live* (opcional): `tests/live/`, marcados `@pytest.mark.live`, desligados por padrão (`-m "not live"` em `pyproject.toml`). Chamam o IRSA real com M101 (`ra=210.80227`, `dec=54.34895`, `collection=spherex_qr3`).
- **Frameworks**: `pytest`, `pytest-asyncio`, `respx`, `httpx`.
- **Dados de teste**:
  - `sia_m101_qr3.xml`: gravar uma vez a resposta real de `https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=CIRCLE 210.80227 54.34895 0.001&MAXREC=50` e salvar como fixture. Se não houver rede no ambiente do agente, gerar um VOTable sintético com as mesmas colunas e os valores do exemplo da seção 9.
  - `sia_empty.xml` e `sia_overflow.xml`: VOTables sintéticos.
  - FITS sintético: fixture `pytest` que gera um MEF em memória com HDUs `IMAGE` (float32, fundo + ruído gaussiano + estrelas gaussianas em posições conhecidas), `FLAGS` (int32, header com `MP_HOT`, `MP_SOURCE` etc.) e `ZODI` (constante), WCS `TAN` com escala 6,15″/px e rotação parametrizável.
- **CI**: GitHub Actions em `backend/**`: `uv sync`, `ruff check`, `ruff format --check`, `pytest -m "not live"`, `docker build`. Arquivo `.github/workflows/backend.yml` é a única exceção permitida a CON-009.
- **Cobertura**: mínimo de 80% de linhas em `app/processing` e `app/services`.
- **Desempenho**: fora do escopo de automação nesta versão. Registrar a duração de cada etapa (SIA, cutout, processamento) nos logs.

## 7. Justificativa e contexto

- **Por que SIA2 + cutout e não S3/arquivo completo**: cada MEF tem ~70 MB; o cutout do IRSA devolve só a região pedida, com todas as HDUs (IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE). Isso reduz tráfego e memória em ordens de grandeza e independe de credenciais de nuvem.
- **Por que `spherex_qr3` como padrão**: em testes manuais de 2026-11-14, `spherex_qr3` retornou imagens para M101, enquanto `spherex_dr1` retornou vazio ou `502 Proxy Error`. `dr1` continua permitida via parâmetro.
- **Por que VOTable e não JSON**: VOTable é o formato padrão do SIA2 e tem parser robusto no astropy. A resposta JSON do IRSA é uma conversão não padronizada do VOTable.
- **Por que reprojetar (`align=true`)**: cada visita aponta o telescópio com rotação diferente. Sem reprojeção, a mesma região aparece girada entre datas e a comparação visual (objetivo do desafio) fica impossível.
- **Por que expor/aceitar escala**: cada imagem normalizada pelos próprios percentis muda de brilho entre datas e confunde a percepção de mudança. Reutilizar a escala da primeira imagem estabiliza o "blink".
- **Por que não mascarar `SOURCE`**: o bit indica onde há fontes astronômicas; mascará-lo removeria as estrelas.
- **Por que transparência em vez de preto**: distingue "sem dados" de "céu escuro", o que é importante para a didática.
- **Por que o semáforo e o processamento fora do event loop**: astropy/reproject são CPU-bound; sem isso uma renderização bloqueia todas as requisições do processo e várias simultâneas podem esgotar a memória do container.
- **Por que interfaces nos clientes**: o cache (próxima spec) será um wrapper de `SiaClient`/`CutoutClient` e/ou do PNG final, sem tocar nos serviços.
- **Por que agnóstico de infra**: o time pode hospedar em GCP, Azure ou Render. Container + `PORT` + env vars + stdout é o denominador comum das três.
- **Limitação conhecida (LVF)**: dentro de uma mesma imagem, o comprimento de onda varia ao longo do detector. Duas datas do mesmo detector podem ter medido a mesma estrela em comprimentos de onda ligeiramente diferentes. Para visualização pública isso é aceitável; a v1 não corrige isso e informa apenas a faixa do detector.

## 8. Dependências e integrações externas

### Sistemas externos

- **EXT-001**: IRSA SIA2 (`https://irsa.ipac.caltech.edu/SIA`) — busca de imagens por posição/tempo/coleção. HTTP GET, resposta VOTable. Público, sem autenticação.
- **EXT-002**: IRSA IBE Cutouts (`https://irsa.ipac.caltech.edu/ibe/data/...?center=ra,dec&size=deg`) — recorte server-side do MEF. Unidades padrão em graus; RA é reduzida ao intervalo válido pelo servidor; perto da borda, o recorte pode não conter o centro pedido.

### Serviços de terceiros

- **SVC-001**: Nenhum além do IRSA. Não há SLA; o IRSA pode ficar lento ou fora do ar (justifica timeouts, retries e o cache futuro).

### Infraestrutura

- **INF-001**: Qualquer runtime de container que injete `PORT` e permita saída HTTPS para `irsa.ipac.caltech.edu`. Recomendado: 1 vCPU, 1–2 GiB de RAM por instância.

### Dados

- **DAT-001**: Spectral Image MEFs do SPHEREx (Level 2), 2040×2040 px, 6,15″/px, unidades MJy/sr. Coleções `spherex_qr3`, `spherex_qr3_deep`, `spherex_dr1`, `spherex_dr1_deep`. Atualização semanal pelo IRSA.

### Plataforma e bibliotecas (por capacidade)

- **PLT-001**: Python ≥ 3.12.
- **PLT-002**: Framework web ASGI com geração automática de OpenAPI (FastAPI) e servidor ASGI (Uvicorn).
- **PLT-003**: Cliente HTTP assíncrono com timeouts e streaming (httpx).
- **PLT-004**: Biblioteca astronômica para FITS, WCS, VOTable, tempo e stretches (astropy).
- **PLT-005**: Reprojeção de imagens entre WCS (reproject).
- **PLT-006**: Computação numérica (numpy).
- **PLT-007**: Lookup de colormaps (matplotlib, sem pyplot) e codificação PNG (Pillow).
- **PLT-008**: Configuração tipada por env (pydantic-settings).

### Conformidade

- **COM-001**: Dados do SPHEREx são públicos. O README e o OpenAPI devem incluir crédito: "Data: NASA/JPL-Caltech/IPAC — SPHEREx, via NASA/IPAC Infrared Science Archive (IRSA)".

## 9. Exemplos e casos de borda

### 9.1 Linha real do SIA (`spherex_qr3`, M101, consultada em 2026-11-14)

```text
obs_id               = 2026W20_2A_0464_3
energy_bandpassname  = SPHEREx-D2
dataproduct_subtype  = science
em_min / em_max      = 1.10330e-06 / 1.64990e-06   (metros)
t_min / t_max        = 61177.456981 / 61177.458313 (MJD)
t_exptime            = 113.5826                    (s)
s_ra / s_dec         = 212.023200 / 52.652924
s_region             = POLYGON ICRS 211.776795 55.094819 216.055743 52.719557 212.228129 50.179011 207.966541 52.435542 211.776795 55.094819
access_url           = https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W20_2A/l2b-v27-2026-267/2/level2_2026W20_2A_0464_3D2_spx_l2b-v27-2026-267.fits
access_estsize       = 68205 (kB)
s_xel1 / s_xel2      = 2040 / 2040
s_pixel_scale        = 6.150
```

### 9.2 Requisições de exemplo

```bash
# Datas disponíveis para M101
curl "http://localhost:8000/epochs?ra=210.80227&dec=54.34895"

# Somente detector D2 em maio de 2026
curl "http://localhost:8000/epochs?ra=210.80227&dec=54.34895&detector=D2&start_time=2026-05-01T00:00:00Z&end_time=2026-05-31T23:59:59Z"

# Imagem alinhada, padrão
curl -o m101.png -D - "http://localhost:8000/image?ra=210.80227&dec=54.34895&observation_id=2026W20_2A_0464_3&detector=D2"

# Mesma região, outra data, reaproveitando a escala da primeira
curl -o m101_b.png "http://localhost:8000/image?ra=210.80227&dec=54.34895&observation_id=<outro_id>&detector=D2&scale_min=0.0123&scale_max=4.5678"
```

### 9.3 Casos de borda

| Caso | Comportamento esperado |
|---|---|
| RA = 0 ou próxima de 360 (ex.: 359.999) | Funciona; RA = 360 é inválida (422). Reprojeção trata a continuidade. |
| Dec = ±90 (polo) | Funciona; projeção TAN centrada no polo é válida. |
| Posição sem cobertura ainda | `/epochs` → 200 com listas vazias. |
| Posição perto da borda da imagem | O cutout vem parcial; após reprojeção, a área sem dados fica transparente. `X-Valid-Pixel-Fraction` < 1. |
| Posição fora da observation pedida | `/image` → 404 `OBSERVATION_NOT_FOUND` (o SIA não devolve aquela linha para essa posição). |
| Observation sem o detector pedido | `/image` → 404 `OBSERVATION_NOT_FOUND`. |
| Todos os pixels mascarados | `/image` → 422 `EMPTY_IMAGE`. |
| `size` muito pequeno (0.01° ≈ 6 px) | Saída com mínimo de 16 px de lado. |
| Cutout gzipado | Descomprimir pelo magic number `1f 8b`. |
| VOTable com `QUERY_STATUS = ERROR` | 502 `UPSTREAM_ERROR`, com a mensagem do IRSA nos logs (não na resposta). |
| VOTable com `QUERY_STATUS = OVERFLOW` | 200 com `truncated: true`. |
| Coleção `spherex_dr1` respondendo 502 | 502 `UPSTREAM_ERROR` após retry. |
| Linhas duplicadas no SIA (mesmo obs_id + detector) | Manter a primeira; logar `warning`. |
| `ZODI` ausente com `subtract_zodi=true` | Seguir sem subtração; logar `warning`. |

## 10. Critérios de validação

- **VAL-001**: Todos os critérios AC-001 a AC-019 passam (automatizados, exceto AC-018, verificado manualmente ou no CI com `docker build`).
- **VAL-002**: `ruff check` e `ruff format --check` sem erros.
- **VAL-003**: `pytest -m "not live"` passa sem acesso à rede.
- **VAL-004**: Cobertura ≥ 80% em `app/processing` e `app/services`.
- **VAL-005**: `/openapi.json` valida em um validador OpenAPI 3 e todos os parâmetros têm `description` e `example`.
- **VAL-006**: Grep no código não encontra imports de SDKs de nuvem (AC-019) nem `matplotlib.pyplot` (CON-008).
- **VAL-007**: (Live) `GET /epochs` para M101 em `spherex_qr3` retorna ≥ 1 observation, e `GET /image` com a primeira observation retorna um PNG visualmente coerente (galáxia/estrelas visíveis, sem faixas, norte para cima).
- **VAL-008**: (Live, primeira execução) Inspecionar o header da HDU `FLAGS` de um cutout real e confirmar a convenção `MP_*` e os nomes de bits de 4.3.1. Registrar o resultado no README; ajustar `FLAGS_REJECT_NAMES` se necessário.
- **VAL-009**: (Live) Confirmar que `WCS(header_IMAGE).celestial` produz coordenadas coerentes com `s_ra`/`s_dec` do SIA (erro < 1 pixel no centro). Se o header usar WCS alternativo (letra de chave), documentar qual chave é a celestial.

## 11. Especificações relacionadas / leitura complementar

- Próxima spec (planejada): `spec-infrastructure-spherex-image-cache.md` — cache de consultas SIA e de PNGs (backend de armazenamento plugável: GCS, R2, disco).
- Próxima spec (planejada): rota `GET /footprints` para desenhar as áreas cobertas no mapa do céu.
- SPHEREx Data Access (IRSA): https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access
- SPHEREx Data Products (IRSA): https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products
- IRSA Image Server Cutouts: https://irsa.ipac.caltech.edu/ibe/cutouts.html
- SPHEREx Cutout Capabilities: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html
- Tutorial SPHEREx Intro (IRSA): https://caltech-ipac.github.io/irsa-tutorials/spherex-intro
- IVOA SIA 2.0: https://www.ivoa.net/documents/SIA/
