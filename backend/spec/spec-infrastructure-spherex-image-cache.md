---
title: SPHEREye — Cache de imagens e consultas em object storage S3 (implementação de referência: Cloudflare R2)
version: 0.2
date_created: 2026-11-15
last_updated: 2026-11-15
owner: Time do hackathon NASA (backend)
tags: [infrastructure, cache, s3, cloudflare-r2, api, python]
---

# Introdução

Esta especificação adiciona uma camada de cache à API do SPHEREye. Ela complementa:

- `spec/spec-tool-spherex-image-api.md` (spec base);
- `spec/spec-tool-spherex-image-quality.md` (tamanho, upscale, RGB e stack).

O cache guarda os **PNGs renderizados** e as **consultas SIA** em um object storage compatível com S3. As imagens em cache são servidas ao navegador diretamente pela **URL pública padrão do R2** (subdomínio `r2.dev`), sem URLs assinadas e sem passar pelo backend.

O código é **S3-first**: tudo é escrito contra a API S3 genérica, e nenhum nome, SDK ou conceito específico de provedor aparece fora da configuração. O provedor em uso é o **Cloudflare R2**. As particularidades necessárias para o R2 funcionar estão na seção 4.8 e são aplicadas por configuração, sem ramificações de código por provedor.

## 1. Propósito e escopo

**Propósito:** guiar o agente de implementação na construção do cache, sem quebrar os contratos existentes de `/epochs` e `/image`.

**Dentro do escopo:**

- Normalização dos parâmetros (quantização de posição e de valores) para aumentar a taxa de acerto do cache.
- Chave de cache determinística e versionada.
- Cache de PNGs (L2: object storage) com metadados em arquivo "sidecar" JSON.
- Cache de resultados SIA (L1: memória do processo; L2: object storage) com TTL.
- Novo parâmetro `response_format` em `/image` (`png`, `json`, `redirect`).
- Proteção contra stampede (single-flight por processo).
- Degradação elegante quando o storage está desligado ou indisponível.
- Configuração S3 genérica e checklist de provisionamento do R2.
- Testes.

**Fora do escopo:**

- Cache dos FITS/cutouts brutos.
- Pré-renderização em lote (job separado, spec futura). Esta spec deve deixar a função de renderização + gravação reutilizável por esse job.
- Invalidação manual via API, autenticação, URLs assinadas e uploads pelo navegador.
- Provisionamento automatizado (Terraform/Wrangler). O provisionamento é manual, pelo checklist da seção 4.9.

**Premissas:**

- Frontend na Vercel; backend no Render (container); bucket no Cloudflare R2.
- O bucket é exposto publicamente pela URL pública padrão do R2 (`https://pub-<id>.r2.dev`). Não há domínio personalizado disponível. Isso é uma limitação aceita para o hackathon (ver R2-08 e R2-09).
- Todo o conteúdo do bucket é dado público derivado do arquivo da NASA. Não há dados sensíveis.

## 2. Definições

| Termo | Definição |
|---|---|
| **Object storage S3** | Serviço de armazenamento de objetos que implementa a API do Amazon S3 (`PutObject`, `GetObject`, `HeadObject`, `ListObjectsV2` etc.). |
| **R2** | Object storage da Cloudflare compatível com a API S3, sem cobrança de egress. |
| **Bucket** | Contêiner de objetos no storage. |
| **Key** | Nome (caminho) de um objeto dentro do bucket. |
| **Domínio público** | Hostname HTTPS que serve os objetos do bucket para qualquer pessoa, sem autenticação (`S3_PUBLIC_BASE_URL`). |
| **L1** | Cache em memória do processo (LRU com TTL). Perdido a cada reinício. |
| **L2** | Cache persistente no object storage. Compartilhado entre instâncias e deploys. |
| **Sidecar** | Objeto JSON gravado ao lado de cada PNG com os metadados da renderização. Também funciona como marcador de "gravação concluída". |
| **Hit / Miss / Bypass** | Encontrado no cache / não encontrado (renderizado agora) / cache não usado (desligado ou indisponível). |
| **Stampede** | Várias requisições simultâneas para o mesmo item ausente, todas renderizando a mesma coisa. |
| **Single-flight** | Técnica em que só a primeira requisição de uma chave executa o trabalho e as demais aguardam o resultado dela. |
| **Quantização** | Arredondamento de um valor contínuo para uma grade fixa. Aqui, para que posições quase iguais gerem a mesma chave de cache. |
| **`RENDER_VERSION`** | Constante no código que identifica a versão do algoritmo de renderização. Mudá-la invalida logicamente todo o cache de imagens. |
| **URL pública `r2.dev`** | Subdomínio gerenciado pela Cloudflare que expõe o bucket publicamente, sem domínio próprio. Destinado a uso não produtivo e sujeito a rate limit. |

## 3. Requisitos, restrições e diretrizes

### 3.1 Normalização de parâmetros

- **REQ-501**: Antes de qualquer outra etapa (cache ou renderização), `/image` e `/epochs` devem normalizar os parâmetros. **A renderização usa os valores normalizados**, garantindo que o conteúdo da imagem corresponda exatamente à chave.
- **REQ-502**: Posição: `ra` e `dec` são arredondados para múltiplos de `POSITION_QUANTUM_ARCSEC / 3600` graus (default `6.15″`, ou seja 1 pixel nativo). Depois, `ra = ra mod 360` e `dec` limitado a `[-90, 90]`. A imagem resultante fica deslocada no máximo meio pixel do ponto pedido.
- **REQ-503**: Demais floats: `size` com 2 casas decimais; `percentile_low`/`percentile_high` com 1 casa; `scale_min`/`scale_max`/`scale_mins`/`scale_maxs` com 6 algarismos significativos.
- **REQ-504**: Parâmetros que não afetam a saída são **removidos** da chave: `colormap` em `mode=rgb`; `percentile_low`/`percentile_high` quando há escala explícita; `detectors` em `mode=single`; `detector` em `mode=rgb`.
- **REQ-505**: `/image` passa a devolver os headers `X-Center-Ra` e `X-Center-Dec` (valores normalizados, 6 casas decimais). Em `/epochs`, `query.ra`/`query.dec` passam a refletir os valores normalizados.

### 3.2 Chave de cache

- **REQ-511**: Chave de imagem:
  `{S3_KEY_PREFIX}images/{RENDER_VERSION}/{collection}/{observation_id}/{hash}.png`, com sidecar em `... /{hash}.json`.
- **REQ-512**: `hash` = os primeiros 32 caracteres hexadecimais do SHA-256 do JSON canônico dos parâmetros normalizados (`json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`), incluindo `RENDER_VERSION` e `collection`.
- **REQ-513**: `RENDER_VERSION` é uma constante em `app/processing/__init__.py` (valor inicial `"r1"`). Qualquer mudança que altere pixels de saída (stretch, máscara, reprojeção, stack, upscale, colormap, defaults) **exige** incrementar essa constante. Isso deve estar escrito em um comentário junto da constante e no README.
- **REQ-514**: Chave SIA: `{S3_KEY_PREFIX}sia/{collection}/{hash}.json`, com `hash` calculado sobre `{collection, ra, dec, radius, time_start_mjd, time_end_mjd, maxrec}` normalizados.
- **REQ-515**: Keys usam somente `[A-Za-z0-9/_.-]`. `observation_id` já é validado pela regex da spec base. Comprimento total < 512 bytes.

### 3.3 Cache de imagens

- **REQ-521**: Fluxo de `/image` com cache habilitado:
  1. Normalizar (3.1) e calcular a chave (3.2).
  2. Procurar o sidecar: L1 (memória) e depois L2 (`GetObject` do sidecar).
  3. **Hit**: responder conforme `response_format` (4.2) **sem** chamar o IRSA nem renderizar.
  4. **Miss**: entrar no single-flight da chave (REQ-531), renderizar com o pipeline existente e gravar no L2 (REQ-522). Depois responder.
- **REQ-522**: Ordem de gravação: (1) `PutObject` do PNG; (2) `PutObject` do sidecar. O sidecar só é gravado se o PNG tiver sido gravado com sucesso. Leitores consideram o item existente **somente** se o sidecar existir.
- **REQ-523**: Atributos do objeto PNG: `ContentType: image/png`, `CacheControl: public, max-age=31536000, immutable`. Atributos do sidecar: `ContentType: application/json`, `CacheControl: public, max-age=31536000, immutable`. Nenhum outro parâmetro de escrita (sem ACL, storage class, tagging, SSE, object lock — ver 4.8).
- **REQ-524**: Conteúdo do sidecar (schema na seção 4.4): parâmetros normalizados, todos os valores que hoje vão em headers `X-*` (spec base e v0.1), `key`, `public_url`, `render_version`, `created_at`, `bytes` e `sha256` do PNG.
- **REQ-525**: Com `response_format=png` e miss, a gravação no L2 pode ser feita **em background** após a resposta (FastAPI `BackgroundTasks`), para não somar a latência do upload. Com `json` ou `redirect`, a gravação deve terminar **antes** da resposta, porque a URL pública precisa existir.
- **REQ-526**: Nunca cachear respostas de erro, incluindo `EMPTY_IMAGE` e `REQUEST_TOO_LARGE`.
- **REQ-527**: Hit com `response_format=png`: baixar o PNG pelo S3 (`GetObject`) e devolvê-lo com os headers reconstruídos do sidecar. O header `X-Cache: HIT` indica que veio do cache.

### 3.4 Concorrência

- **REQ-531**: Single-flight por processo: um dicionário `key → asyncio.Future`. A primeira requisição de uma chave executa renderização + gravação; as demais aguardam o mesmo Future e recebem o mesmo resultado (ou o mesmo erro). A entrada é removida ao terminar, com sucesso ou erro.
- **REQ-532**: As requisições que aguardam no single-flight **não** ocupam vaga no semáforo de renderização (`MAX_CONCURRENT_RENDERS`).
- **REQ-533**: Entre instâncias diferentes não há coordenação: renderizações duplicadas são aceitáveis, porque a gravação é idempotente (mesma chave, mesmo conteúdo). Um `PutObject` que falhe com HTTP 429 ou `SlowDown` é tratado como sucesso, logado como `info`, desde que um `HeadObject` subsequente confirme que o objeto existe.

### 3.5 Cache de consultas SIA

- **REQ-541**: O `SiaClient` da spec base ganha um wrapper `CachedSiaClient` (PAT-003 da spec base) que implementa a mesma interface. Serviços e rotas não mudam.
- **REQ-542**: L1: LRU em memória com até `MEMORY_CACHE_MAX_ITEMS` (default `512`) e TTL `SIA_CACHE_TTL_SECONDS` (default `21600`, 6 h).
- **REQ-543**: L2: objeto JSON com `{"fetched_at": "<ISO>", "records": [...]}` (lista serializada de `ImageRecord`). No momento da leitura, se `now - fetched_at > SIA_CACHE_TTL_SECONDS`, tratar como miss e reconsultar o IRSA.
- **REQ-544**: O L2 do SIA usa `CacheControl: no-store`. Esses objetos não são feitos para o navegador e o TTL é controlado pelo código.
- **REQ-545**: Se o IRSA falhar (timeout/5xx) e existir uma entrada SIA vencida no L2, usá-la (*stale-if-error*), logando `warning` com `event="sia_stale_served"`. Isso protege a demo contra instabilidade do IRSA.
- **REQ-546**: `/epochs` e a resolução interna de `/image` usam o mesmo cache SIA.
- **REQ-547**: O L1 também guarda sidecars de imagens (mesma LRU, chave = key do sidecar, TTL `IMAGE_META_L1_TTL_SECONDS`, default `3600`).

### 3.6 Degradação

- **REQ-551**: `CACHE_ENABLED=false`: nenhuma chamada S3. `/image` se comporta como na v0.1, com `X-Cache: BYPASS`. `response_format=json` e `redirect` passam a apontar para a própria API (REQ-553).
- **REQ-552**: Storage indisponível (erro de rede, 5xx, credenciais inválidas) em leitura ou escrita: **não falhar a requisição**. Logar `error` com `event="storage_unavailable"` e seguir como `BYPASS`. Após 3 falhas consecutivas, abrir um circuit breaker por `STORAGE_CIRCUIT_OPEN_SECONDS` (default `60`), durante o qual o storage não é chamado.
- **REQ-553**: Em `BYPASS`, `json` devolve `url` = `{API_PUBLIC_BASE_URL}/image?{parâmetros normalizados}&response_format=png` e `redirect` responde `302` para essa mesma URL.
- **REQ-554**: `GET /health` passa a incluir `"cache": {"enabled": <bool>, "circuit_open": <bool>}`, sem chamar o storage.

### 3.7 Segurança

- **SEC-501**: Credenciais S3 só via variáveis de ambiente. Nunca logar `S3_SECRET_ACCESS_KEY`, nem incluí-la em erros. O objeto de settings deve usar `SecretStr`.
- **SEC-502**: O backend nunca recebe keys do cliente: elas são sempre derivadas dos parâmetros normalizados. Isso impede leitura/escrita de caminhos arbitrários no bucket.
- **SEC-503**: A credencial deve ter permissão **somente de objetos** (ler e escrever) em **um único bucket**. O código não pode depender de permissões de bucket: nada de `CreateBucket`, `PutBucketCors`, `PutBucketLifecycleConfiguration` ou similares em runtime.
- **SEC-504**: `public_url` é montada só a partir de `S3_PUBLIC_BASE_URL` (validada no startup: `https://`, sem query string, sem barra final) e da key.

### 3.8 Restrições

- **CON-501**: Biblioteca S3: `boto3` (cliente síncrono). Todas as chamadas rodam fora do event loop (`anyio.to_thread.run_sync` ou `run_in_threadpool`). Um único cliente por processo, criado no lifespan (clientes boto3 são thread-safe; sessions não).
- **CON-502**: Nenhum identificador, import ou `if` específico de provedor (`r2`, `cloudflare`, `gcs`, `aws`) no código. Diferenças de provedor são resolvidas por configuração (4.6 e 4.8).
- **CON-503**: Nenhum SDK da Cloudflare (Workers, Wrangler, API REST) no backend.
- **CON-504**: Sem URLs assinadas.
- **CON-505**: Os contratos existentes (parâmetros, headers, erros) continuam válidos. `response_format` default `png` mantém o comportamento anterior.

### 3.9 Diretrizes e padrões

- **PAT-501**: Interface `ObjectStore` (`typing.Protocol`) em `app/storage/protocols.py`: `get_bytes(key) -> bytes | None`, `put_bytes(key, data, content_type, cache_control) -> None`, `exists(key) -> bool`, `public_url(key) -> str`. Implementações: `S3ObjectStore` (boto3) e `InMemoryObjectStore` (somente para testes; com `CACHE_ENABLED=false` nenhum store é instanciado).
- **PAT-502**: Serviço `ImageCacheService` em `app/services/image_cache_service.py`, que orquestra normalização → chave → lookup → single-flight → render → gravação. A função `render_and_store(params) -> Sidecar` deve ser pública e reutilizável pelo futuro job de pré-renderização.
- **PAT-503**: Erros S3 não encontrados (`NoSuchKey`, HTTP 404) são retornados como `None` pelo `ObjectStore`, não como exceção.
- **GUD-501**: Logar por requisição: `cache_status`, `cache_layer` (`l1`/`l2`/`none`), `key`, duração do lookup e do upload.

## 4. Interfaces e contratos de dados

### 4.1 Estrutura de diretórios (acréscimos)

```
backend/app/
├── storage/
│   ├── __init__.py
│   ├── protocols.py         # ObjectStore
│   ├── s3_store.py          # S3ObjectStore (boto3)
│   ├── memory_store.py      # InMemoryObjectStore (testes)
│   └── circuit_breaker.py
├── cache/
│   ├── normalize.py         # REQ-501..505
│   ├── keys.py              # REQ-511..515
│   ├── lru.py               # L1 (pode usar cachetools.TTLCache)
│   └── singleflight.py      # REQ-531
├── clients/
│   └── cached_sia.py        # CachedSiaClient (REQ-541..546)
└── services/
    └── image_cache_service.py
```

### 4.2 `GET /image` — novo parâmetro `response_format`

| Valor | Hit | Miss | Bypass |
|---|---|---|---|
| `png` (default) | `200 image/png` (bytes do storage), headers do sidecar, `X-Cache: HIT` | `200 image/png` renderizado, `X-Cache: MISS`, upload em background | `200 image/png`, `X-Cache: BYPASS` |
| `json` | `200 application/json` (4.3), `cache_status: "hit"` | renderiza, grava, depois `200` com `cache_status: "miss"` | `200` com `cache_status: "bypass"` e `url` da API (REQ-553) |
| `redirect` | `302 Location: {public_url}` + headers `X-*` | renderiza, grava, depois `302` | `302` para a URL da API |

Notas obrigatórias no OpenAPI:

- `json` é o modo recomendado para o frontend: devolve a URL pública e todos os metadados em uma chamada.
- `redirect` serve para usar a API diretamente em `<img src>`. Navegadores e `fetch` seguem o redirect e **não expõem** os headers `X-*` da resposta 302. Para obter metadados (ex.: escala), use `json`.
- Em `redirect`, a resposta 302 leva `Cache-Control: public, max-age=86400`.

### 4.3 Resposta `response_format=json`

```json
{
  "url": "https://pub-0123456789abcdef.r2.dev/images/r1/spherex_qr3/2026W20_2A_0464_3/3f9a0c1e5b7d2a4c8e6f1b3d5a7c9e0f.png",
  "cache_status": "hit",
  "key": "images/r1/spherex_qr3/2026W20_2A_0464_3/3f9a0c1e5b7d2a4c8e6f1b3d5a7c9e0f.png",
  "render_version": "r1",
  "created_at": "2026-11-15T12:03:44Z",
  "params": {
    "collection": "spherex_qr3",
    "ra": 210.8015,
    "dec": 54.348917,
    "observation_id": "2026W20_2A_0464_3",
    "mode": "single",
    "detector": "D2",
    "size": 1.0,
    "upscale": 1,
    "align": true,
    "stack": false,
    "subtract_zodi": true,
    "stretch": "asinh",
    "colormap": "inferno",
    "percentile_low": 1.0,
    "percentile_high": 99.5
  },
  "image": {
    "width": 585,
    "height": 585,
    "bytes": 412337,
    "sha256": "<hex>",
    "pixel_scale_arcsec": 6.15,
    "native_pixel_scale_arcsec": 6.15,
    "valid_pixel_fraction": 0.982
  },
  "observation": {
    "observation_id": "2026W20_2A_0464_3",
    "observation_time": "2026-05-17T10:58:03Z",
    "detectors": ["D2"],
    "wavelength_min_um": [1.1033],
    "wavelength_max_um": [1.6499]
  },
  "scale": {
    "min": [0.0123],
    "max": [4.5678]
  },
  "stack": null
}
```

Regras:

- Valores por canal são sempre **listas** (1 item em `single`, 3 em `rgb`, ordem R,G,B).
- `stack` é `null` quando `stack=false`. Caso contrário: `{"count": [..], "observation_ids": [..], "time_span_seconds": <float>, "truncated": <bool>}`.
- O mesmo objeto (sem `url` e `cache_status`) é o conteúdo do sidecar (4.4).

### 4.4 Sidecar

Objeto `{hash}.json`, com o mesmo conteúdo da resposta 4.3, **exceto** `cache_status`. Inclui `public_url` (igual a `url`) e um campo `schema_version: 1`. Ao ler um sidecar com `schema_version` desconhecida, tratar como miss.

### 4.5 Headers (acréscimos)

| Header | Valores |
|---|---|
| `X-Cache` | `HIT`, `MISS`, `BYPASS` |
| `X-Center-Ra`, `X-Center-Dec` | posição normalizada |
| `X-Render-Version` | ex.: `r1` |

Adicionar ao `Access-Control-Expose-Headers` e ao OpenAPI.

### 4.6 Variáveis de ambiente

| Variável | Obrigatória se cache ligado | Default | Descrição |
|---|---|---|---|
| `CACHE_ENABLED` | — | `false` | Liga o cache. Com `false`, nenhuma das variáveis `S3_*` é exigida. |
| `S3_ENDPOINT_URL` | sim | — | Endpoint da API S3. R2: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. |
| `S3_REGION` | — | `auto` | R2: `auto`. AWS: a região do bucket. |
| `S3_BUCKET` | sim | — | Nome do bucket. |
| `S3_ACCESS_KEY_ID` | sim | — | |
| `S3_SECRET_ACCESS_KEY` | sim | — | `SecretStr`. |
| `S3_ADDRESSING_STYLE` | — | `path` | `path` ou `virtual`. |
| `S3_CHECKSUM_MODE` | — | `when_required` | Valor de `request_checksum_calculation` e `response_checksum_validation` do botocore (`when_required` ou `when_supported`). |
| `S3_CONNECT_TIMEOUT_SECONDS` | — | `5` | |
| `S3_READ_TIMEOUT_SECONDS` | — | `20` | |
| `S3_MAX_ATTEMPTS` | — | `3` | Retries do botocore (`mode="standard"`). |
| `S3_MAX_POOL_CONNECTIONS` | — | `20` | |
| `S3_PUBLIC_BASE_URL` | sim | — | Domínio público, ex.: `https://pub-<id>.r2.dev`. Sem barra final. |
| `S3_KEY_PREFIX` | — | `""` | Ex.: `dev/` ou `prod/` para separar ambientes no mesmo bucket. Se não vazio, deve terminar com `/`. |
| `API_PUBLIC_BASE_URL` | sim | — | URL pública do backend (REQ-553). Ex.: `https://sphereye-api.onrender.com`. |
| `POSITION_QUANTUM_ARCSEC` | — | `6.15` | REQ-502. |
| `SIA_CACHE_TTL_SECONDS` | — | `21600` | REQ-542/543. |
| `IMAGE_META_L1_TTL_SECONDS` | — | `3600` | REQ-547. |
| `MEMORY_CACHE_MAX_ITEMS` | — | `512` | REQ-542. |
| `STORAGE_CIRCUIT_OPEN_SECONDS` | — | `60` | REQ-552. |

Validação no startup: se `CACHE_ENABLED=true` e alguma variável obrigatória faltar, **falhar o boot** com mensagem clara listando as variáveis ausentes, sem exibir valores.

### 4.7 Configuração do cliente S3

```python
from botocore.config import Config
import boto3

config = Config(
    signature_version="s3v4",
    s3={"addressing_style": settings.s3_addressing_style},
    retries={"max_attempts": settings.s3_max_attempts, "mode": "standard"},
    connect_timeout=settings.s3_connect_timeout_seconds,
    read_timeout=settings.s3_read_timeout_seconds,
    max_pool_connections=settings.s3_max_pool_connections,
    request_checksum_calculation=settings.s3_checksum_mode,
    response_checksum_validation=settings.s3_checksum_mode,
)

client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    region_name=settings.s3_region,
    aws_access_key_id=settings.s3_access_key_id,
    aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
    config=config,
)
```

Exigir `boto3 >= 1.36` (os parâmetros de checksum do `Config` existem a partir dessa versão).

### 4.8 Particularidades do Cloudflare R2 (aplicadas só por configuração)

| # | Particularidade | Como tratar |
|---|---|---|
| R2-01 | **Endpoint por conta**: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. Buckets com jurisdição UE usam `https://<ACCOUNT_ID>.eu.r2.cloudflarestorage.com`. | `S3_ENDPOINT_URL`. |
| R2-02 | **Região `auto`**: na API S3, a região de um bucket R2 é `auto`; valor vazio e `us-east-1` são aceitos como apelidos. | `S3_REGION=auto`. |
| R2-03 | **Checksums do boto3 ≥ 1.36**: desde jan/2025, os SDKs da AWS calculam checksums CRC32 por padrão, e vários storages S3-compatíveis rejeitaram isso. A correção documentada é `WHEN_REQUIRED` em `request_checksum_calculation` e `response_checksum_validation`. | `S3_CHECKSUM_MODE=when_required` (default). Também funciona com AWS S3. |
| R2-04 | **Sem ACLs**: o R2 não implementa `x-amz-acl` nem os headers `x-amz-grant-*`. Pela API S3, os objetos são sempre privados; o acesso público vem da URL pública `r2.dev` habilitada no bucket. | Nunca enviar `ACL=` nem `Grant*` (REQ-523). |
| R2-05 | **Outros parâmetros de escrita não suportados**: `x-amz-tagging`, `x-amz-storage-class`, SSE-KMS (`x-amz-server-side-encryption-*`), object lock e `x-amz-expected-bucket-owner`. | Não enviar `Tagging`, `StorageClass`, `ServerSideEncryption`, `ObjectLock*` nem `ExpectedBucketOwner`. Um teste deve verificar isso (AC-516). |
| R2-06 | **Metadados de objeto limitados** (8.192 bytes no total). | Metadados ficam no sidecar JSON, não em `x-amz-meta-*`. |
| R2-07 | **Escritas concorrentes na mesma key** em alta taxa retornam HTTP 429. | Single-flight (REQ-531) + tratamento de 429 (REQ-533). |
| R2-08 | **`r2.dev` tem rate limit**: a Cloudflare limita o acesso pela URL pública padrão (na casa de centenas de requisições por segundo) e responde `429` ao exceder; o throughput também pode ser limitado. É suficiente para a demo, mas não para tráfego alto. | `S3_PUBLIC_BASE_URL` = URL `r2.dev` do bucket. Mitigações: `Cache-Control: immutable` (o navegador não pede a mesma imagem de novo) e fallback no frontend (9.1): se a `<img>` falhar, recarregar via `{API}/image?...&response_format=png`, que lê o objeto pela API S3 e não passa pelo `r2.dev`. Se no futuro houver domínio próprio, basta trocar `S3_PUBLIC_BASE_URL`; nenhum código muda. |
| R2-09 | **Sem cache de borda (CDN) no `r2.dev`**: recursos como cache da Cloudflare, WAF e regras de transformação exigem domínio personalizado. | Cada visualização nova sai do bucket. O cache efetivo fica no navegador, via `Cache-Control: public, max-age=31536000, immutable` gravado no objeto (REQ-523). Não depender de `cf-cache-status`. |
| R2-10 | **CORS**: necessário se o frontend ler pixels da imagem em `<canvas>` (ex.: efeito blink, comparação) ou buscá-la por `fetch`. `<img>` simples não precisa. | Configurar a política CORS no bucket (4.9, item 5). No frontend, usar `crossOrigin="anonymous"` em **todas** as `<img>` da URL pública, para que o cache do navegador não guarde uma versão sem CORS e depois a reutilize num `<canvas>`. |
| R2-11 | **Credenciais**: chaves S3 do R2 vêm de um **R2 API Token**. O Secret Access Key só é mostrado uma vez. | Token com permissão *Object Read & Write* restrita ao bucket (SEC-503). |
| R2-12 | **TTL de objetos**: não existe por objeto; usar *lifecycle rules* do bucket por prefixo. | Regra "deletar objetos após 7 dias" no prefixo `{S3_KEY_PREFIX}sia/` (4.9, item 6). O código continua aplicando o TTL de 6 h (REQ-543). |
| R2-13 | **Sem operações de bucket em runtime**: o token de objetos pode não ter permissão para elas. | Nenhuma chamada de bucket no startup ou no health (SEC-503). |

### 4.9 Checklist de provisionamento (manual, fora do código)

Documentar no `backend/README.md` (seção "Cache / Storage"):

1. Criar o bucket (ex.: `sphereye-images`), localização automática.
2. Criar um R2 API Token: permissão *Object Read & Write*, escopo **apenas** esse bucket. Guardar `Access Key ID`, `Secret Access Key` e o endpoint S3 mostrado.
3. Em *Settings → Public Development URL*, clicar em *Enable* e confirmar. Copiar a URL exibida (`https://pub-<id>.r2.dev`) para `S3_PUBLIC_BASE_URL`.
4. Não configurar domínio personalizado (indisponível neste projeto).
5. Em *Settings → CORS Policy*:

   ```json
   [
     {
       "AllowedOrigins": ["*"],
       "AllowedMethods": ["GET", "HEAD"],
       "AllowedHeaders": ["*"],
       "ExposeHeaders": ["Content-Length", "Content-Type", "ETag"],
       "MaxAgeSeconds": 86400
     }
   ]
   ```

   `"*"` é adotado porque todo o conteúdo é público e as previews da Vercel geram URLs diferentes a cada deploy. Para restringir, trocar por `["http://localhost:3000", "https://<projeto>.vercel.app"]`.
6. Em *Settings → Object lifecycle rules*: deletar objetos com prefixo `sia/` (ou `{S3_KEY_PREFIX}sia/`) após 7 dias.
7. Verificação: `curl -I https://pub-<id>.r2.dev/<key-de-teste>.png`. Esperado: `200`, `content-type: image/png` e `cache-control` com `immutable`. Repetir com `-H "Origin: http://localhost:3000"` e conferir `access-control-allow-origin`.
8. Configurar no Render as variáveis da seção 4.6 e `CACHE_ENABLED=true`.

## 5. Critérios de aceitação

- **AC-501**: Dadas duas requisições `/image` com `ra=210.80227` e `ra=210.80180` (ambos arredondam para `210.8015`) e os demais parâmetros iguais, então ambas geram a mesma key, a segunda tem `X-Cache: HIT`, e as duas trazem `X-Center-Ra: 210.801500`. Dado `ra=210.80250` (arredonda para `210.803208`), então a key é outra.
- **AC-502**: Dado `ra=359.9999` com quantização que arredonda para `360.0`, então o valor normalizado é `0.0`.
- **AC-503**: Dado `mode=rgb&colormap=gray` e `mode=rgb&colormap=viridis`, então a key é a mesma (REQ-504).
- **AC-504**: Dada a troca de `RENDER_VERSION` de `r1` para `r2`, então todas as keys de imagem mudam e as de SIA não.
- **AC-505**: Dado cache habilitado com `InMemoryObjectStore`, quando chamo `/image` duas vezes com `response_format=json`, então a primeira tem `cache_status: "miss"`, a segunda `"hit"`, as duas têm a mesma `url`, e o IRSA (mockado) é chamado só na primeira.
- **AC-506**: Dado um miss com `response_format=json`, então no momento da resposta o PNG e o sidecar já existem no store.
- **AC-507**: Dado um miss com `response_format=png`, então a resposta chega antes do upload terminar (store com atraso artificial de 1 s; resposta em < 1 s além do tempo de render), e depois de alguns instantes PNG e sidecar existem.
- **AC-508**: Dado um store em que o PNG existe mas o sidecar não (gravação interrompida), então a requisição é tratada como miss e o item é regravado.
- **AC-509**: Dadas 10 requisições simultâneas para a mesma key ausente, então o pipeline de renderização roda exatamente 1 vez e as 10 recebem `200` com a mesma imagem.
- **AC-510**: Dado `response_format=redirect` com hit, então `302`, `Location` = `S3_PUBLIC_BASE_URL/<key>`, e os headers `X-*` presentes na 302.
- **AC-511**: Dado `CACHE_ENABLED=false`, então nenhuma chamada S3 é feita, `X-Cache: BYPASS`, e `response_format=json` devolve `url` começando por `API_PUBLIC_BASE_URL/image?` com `response_format=png`.
- **AC-512**: Dado um store que lança erro de conexão em todas as chamadas, então `/image` responde `200` com `X-Cache: BYPASS`; após 3 falhas o circuit breaker abre e as próximas requisições, durante `STORAGE_CIRCUIT_OPEN_SECONDS`, não chamam o store.
- **AC-513**: Dada uma entrada SIA no L2 com `fetched_at` há 7 h e o IRSA respondendo 200, então o IRSA é consultado e a entrada é regravada. Com o IRSA respondendo 503, a entrada vencida é usada e é logado `sia_stale_served`.
- **AC-514**: Dadas duas chamadas `/epochs` iguais dentro do TTL, então o IRSA é chamado uma vez. Uma `/image` em seguida, na mesma posição e coleção, também não chama o SIA.
- **AC-515**: Dado `CACHE_ENABLED=true` sem `S3_BUCKET`, então o boot falha listando `S3_BUCKET`, sem exibir valores de outras variáveis.
- **AC-516**: Usando um stub do cliente boto3 que registra os argumentos de `put_object`, então nenhuma chamada contém `ACL`, `Grant*`, `Tagging`, `StorageClass`, `ServerSideEncryption`, `ObjectLock*` ou `ExpectedBucketOwner`, e todas contêm `ContentType` e `CacheControl`.
- **AC-517**: Dado um cliente S3 criado com as settings, então `client.meta.config.request_checksum_calculation` e `response_checksum_validation` são iguais a `S3_CHECKSUM_MODE`.
- **AC-518**: Dado um `PutObject` que retorna 429 e um `HeadObject` que retorna 200, então a gravação é considerada bem-sucedida.
- **AC-519**: Respostas de erro (`404`, `422`, `502`, `504`) nunca geram objetos no store.
- **AC-520**: Grep no código não encontra `r2`, `cloudflare`, `ACL=` nem `generate_presigned_url` fora de README, `.env.example` e comentários desta spec.
- **AC-521**: `/health` inclui `cache.enabled` e `cache.circuit_open` e não faz chamadas S3.

## 6. Estratégia de testes automatizados

- **Unit**: `normalize.py` (quantização, wrap de RA, remoção de parâmetros irrelevantes), `keys.py` (determinismo, estabilidade entre execuções, independência da ordem dos parâmetros), `singleflight.py`, `circuit_breaker.py`, `lru.py`.
- **Integration**: rotas com `InMemoryObjectStore` injetado via `dependency_overrides` e IRSA mockado com `respx` (AC-501 a AC-514, AC-519, AC-521).
- **S3 contract**: `S3ObjectStore` contra `moto` (`mock_aws`) para put/get/exists/404, e contra um stub que registra argumentos (AC-516 a AC-518).
- **Live (opcional)**: `@pytest.mark.live_storage`, desligado por padrão. Usa as variáveis reais com `S3_KEY_PREFIX=test/<uuid>/`; grava e lê um objeto, confere `public_url` com `httpx.get` (200, `content-type`, `cache-control`) e remove o que criou. Esse teste é o único que pode usar `DeleteObject`.
- **Novas dependências de teste**: `moto[s3]`.
- **Cobertura**: ≥ 80% em `app/cache`, `app/storage` e `app/services/image_cache_service.py`.

## 7. Justificativa e contexto

- **Por que S3-first**: R2, AWS S3, GCS (modo interoperável) e MinIO falam o mesmo protocolo. Escrever contra ele mantém o backend agnóstico de infra, requisito das specs anteriores. Trocar de provedor passa a ser só trocar variáveis de ambiente.
- **Por que R2**: egress gratuito e URL pública sem configuração extra. As imagens vão direto do bucket para o navegador, sem consumir banda nem CPU do Render.
- **Por que URL pública em vez de URLs assinadas**: o conteúdo é público, as URLs ficam estáveis e cacheáveis no navegador, e não há expiração para gerenciar.
- **Por que aceitar o `r2.dev`**: não há domínio próprio disponível. O rate limit é compatível com o tráfego de uma demo; o fallback pela API (R2-08) cobre picos, e migrar para domínio próprio depois é só trocar uma variável.
- **Por que quantizar a posição**: sliders produzem coordenadas contínuas; sem quantização, quase toda requisição seria um miss. Meio pixel de diferença (≤ 3″) é imperceptível.
- **Por que sidecar JSON em vez de metadados de objeto**: limite de tamanho de metadados no R2, leitura simples pelo backend e um marcador atômico de "gravação concluída" (o PNG é gravado antes).
- **Por que `response_format=json`**: navegadores não expõem headers de respostas de redirect. O frontend precisa da escala (`scale.min`/`scale.max`) para estabilizar o blink entre datas; o JSON entrega isso junto com a URL pública.
- **Por que cachear o SIA com stale-if-error**: o IRSA já mostrou instabilidade (502 na coleção `spherex_dr1` em 2026-11-14). Com o cache, a demo continua funcionando para posições já consultadas.
- **Por que `RENDER_VERSION` no código e não em env**: a versão está ligada ao algoritmo, que está no código. Uma variável de ambiente esquecida produziria imagens novas sob keys antigas.
- **Por que `immutable`**: a key é derivada de todos os parâmetros e da versão do algoritmo; o conteúdo de uma key nunca muda.

## 8. Dependências e integrações externas

### Sistemas externos

- **EXT-501**: Object storage compatível com S3 (Cloudflare R2). Operações usadas: `PutObject`, `GetObject`, `HeadObject` e, apenas no teste live, `DeleteObject`.
- **EXT-502**: URL pública `r2.dev` do bucket (sem CDN, com rate limit).

### Infraestrutura

- **INF-501**: Bucket R2 provisionado manualmente (4.9) com URL pública `r2.dev`, CORS e lifecycle rule.
- **INF-502**: Saída HTTPS do backend para `*.r2.cloudflarestorage.com`.

### Plataforma

- **PLT-501**: `boto3 >= 1.36` (parâmetros de checksum no `Config`).
- **PLT-502**: LRU com TTL em memória (ex.: `cachetools`).
- **PLT-503**: `moto` para testes.

### Conformidade

- **COM-501**: Os PNGs publicados mantêm o crédito "Data: NASA/JPL-Caltech/IPAC — SPHEREx, via IRSA" no README e no frontend. Opcional: gravar o crédito em um chunk `tEXt` do PNG (`Credit`).

## 9. Exemplos e casos de borda

### 9.1 Uso pelo frontend

```ts
// Recomendado: uma chamada, URL pública + metadados
const res = await fetch(`${API}/image?ra=${ra}&dec=${dec}&observation_id=${id}&detector=D2&response_format=json`);
const meta = await res.json();
img.crossOrigin = "anonymous";
img.onerror = () => {             // fallback se o r2.dev responder 429 (R2-08)
  img.onerror = null;
  img.src = `${API}/image?ra=${ra}&dec=${dec}&observation_id=${id}&detector=D2&response_format=png`;
};
img.src = meta.url;            // servido pela URL pública do R2
const [scaleMin] = meta.scale.min;  // reaproveitar nas outras datas
const [scaleMax] = meta.scale.max;
```

```html
<!-- Atalho sem metadados -->
<img crossorigin="anonymous"
     src="https://<api>/image?ra=83.82&dec=-5.39&observation_id=<id>&mode=rgb&response_format=redirect" />
```

### 9.2 Keys de exemplo

```text
images/r1/spherex_qr3/2026W20_2A_0464_3/3f9a0c1e5b7d2a4c8e6f1b3d5a7c9e0f.png
images/r1/spherex_qr3/2026W20_2A_0464_3/3f9a0c1e5b7d2a4c8e6f1b3d5a7c9e0f.json
sia/spherex_qr3/91be0d44a1c27f3e5d6b8a9c0e1f2a3b.json
dev/images/r1/spherex_qr3/...            # com S3_KEY_PREFIX=dev/
```

### 9.3 Casos de borda

| Caso | Comportamento |
|---|---|
| Sidecar existe, PNG foi apagado manualmente | `json`/`redirect` apontam para uma URL 404. Para apagar itens, sempre apagar o sidecar **antes** do PNG (README). Não há verificação extra por hit. |
| Sidecar corrompido (JSON inválido) ou `schema_version` desconhecida | Tratar como miss, regravar, logar `warning`. |
| Dois deploys com `RENDER_VERSION` diferentes ao mesmo tempo | Cada um lê e grava sob a própria versão; sem conflito. |
| `S3_KEY_PREFIX` sem barra final | Boot falha com mensagem clara. |
| Requisição cancelada pelo cliente durante um miss com single-flight | O trabalho continua até o fim e é gravado; as demais requisições aguardando recebem o resultado. |
| Upload em background falha | Logar `error`; a próxima requisição será miss. |
| Erro no render dentro do single-flight | Todas as requisições aguardando recebem o mesmo erro; nada é gravado. |
| `stack=true` | Entra normalmente no cache; a key inclui `stack` e os parâmetros de orçamento não entram (o conteúdo do sidecar registra o que foi usado). |
| Parâmetros de orçamento (`MAX_*` em env) mudam entre deploys | Podem mudar o resultado de stacks truncados. Aceitável no hackathon; se necessário, incrementar `RENDER_VERSION`. |

## 10. Critérios de validação

- **VAL-501**: AC-501 a AC-521 passam.
- **VAL-502**: Todos os testes das specs base e v0.1 continuam passando com `CACHE_ENABLED=false` e com `CACHE_ENABLED=true` usando `InMemoryObjectStore`.
- **VAL-503**: (Live) Checklist 4.9 executado; o item 7 confirmado e registrado no README.
- **VAL-504**: (Live) Com o backend no Render e o cache ligado, uma segunda visualização da mesma imagem não gera chamada ao IRSA nem renderização (verificar nos logs: `cache_status=hit`).
- **VAL-505**: README atualizado com: variáveis 4.6, checklist 4.9, regra do `RENDER_VERSION`, procedimento de exclusão (sidecar antes do PNG) e exemplos 9.1.

## 11. Especificações relacionadas / leitura complementar

- `spec/spec-tool-spherex-image-api.md` — spec base (v0.1).
- `spec/spec-tool-spherex-image-quality.md` — v0.1.
- Planejada: job de pré-renderização dos alvos da demo, reutilizando `render_and_store`.
- Cloudflare R2 — S3 API compatibility: https://developers.cloudflare.com/r2/api/s3/api/
- Cloudflare R2 — Public buckets: https://developers.cloudflare.com/r2/buckets/public-buckets/
- Cloudflare R2 — Limits: https://developers.cloudflare.com/r2/platform/limits/
- AWS — Data Integrity Protections for Amazon S3 (checksums): https://docs.aws.amazon.com/sdkref/latest/guide/feature-dataintegrity.html
