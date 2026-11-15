# Presets do SPHEREye

Gerado em 2026-11-15T15:11:50Z contra `http://localhost:8001`. Dados: NASA/JPL-Caltech/IPAC — SPHEREx, via IRSA.

A chave de cache depende de todos os parâmetros: para ter HIT, o frontend deve usar a `query` exata de cada imagem (ou os mesmos valores).

| Astro | Catálogo | Tipo | RA | Dec | Size (°) | Visitas | Imagens | Status |
|---|---|---|---|---|---|---|---|---|
| Galáxia de Andrômeda (`m31`) | M31 / NGC 224 | galáxia | 10.6847 | 41.2692 | 2.0 | 4 | 3 | done |
| Nebulosa de Órion (`m42`) | M42 / NGC 1976 | nebulosa | 83.8221 | -5.3911 | 1.0 | 5 | 4 | done |
| Nebulosa do Caranguejo (`m1`) | M1 / NGC 1952 | remanescente de supernova | 83.6331 | 22.0145 | 0.5 | 1 | 2 | done |
| Galáxia do Redemoinho (`m51`) | M51 / NGC 5194 | galáxia | 202.4696 | 47.1953 | 0.5 | 5 | 4 | done |
| Galáxia do Cata-vento (`m101`) | M101 / NGC 5457 | galáxia | 210.8023 | 54.349 | 0.5 | 7 | 5 | done |
| Nebulosa do Anel (`m57`) | M57 / NGC 6720 | nebulosa planetária | 283.3963 | 33.0292 | 0.3 | 5 | 3 | done |
| Nebulosa do Haltere (`m27`) | M27 / NGC 6853 | nebulosa planetária | 299.9013 | 22.7211 | 0.3 | 4 | 3 | done |
| Plêiades (`m45`) | M45 | aglomerado aberto | 56.85 | 24.117 | 2.0 | 1 | 2 | done |
| Nebulosa da Águia (`m16`) | M16 / NGC 6611 | nebulosa | 274.7 | -13.82 | 0.75 | 2 | 3 | done |
| Nebulosa da Lagoa (`m8`) | M8 / NGC 6523 | nebulosa | 270.904 | -24.387 | 1.0 | 3 | 3 | done |
| Galáxia de Bode (`m81`) | M81 / NGC 3031 | galáxia | 148.8883 | 69.0653 | 0.75 | 0 | 0 | no_coverage |
| Galáxia do Sombreiro (`m104`) | M104 / NGC 4594 | galáxia | 189.9975 | -11.6231 | 0.5 | 4 | 4 | done |
| Centro Galáctico (Sgr A*) (`sgra`) | Sgr A* | centro galáctico | 266.4168 | -29.0078 | 1.0 | 2 | 3 | done |
| Nebulosa da Carina (`ngc3372`) | NGC 3372 | nebulosa | 161.264 | -59.684 | 1.5 | 8 | 4 | done |

## Galáxia de Andrômeda (`m31`)

_Grande: ~3° no céu. Núcleo muito brilhante._

- Busca: `GET /epochs?ra=10.6847&dec=41.2692` -> 68 observações, 4 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=10.683917, dec=41.269917.
- Detector `single`: D2; visitas elegíveis: {'single': [1, 3], 'rgb': [3]}; escolhidas: {'single': [1, 3], 'rgb': [3]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 1 | 2026-07-14T06:42:18Z | `2026W29_1A_0252_1` | D2 | não | `ra=10.6847&dec=41.2692&observation_id=2026W29_1A_0252_1&mode=single&size=2.0&upscale=1&detector=D2` |
| single | 3 | 2026-08-06T05:15:21Z | `2026W32_1A_0745_1` | D2 | sim | `ra=10.6847&dec=41.2692&observation_id=2026W32_1A_0745_1&mode=single&size=2.0&upscale=1&detector=D2&scale_min=0.021127120405435563&scale_max=12.133628177642771` |
| rgb | 3 | 2026-08-04T12:32:09Z | `2026W32_1A_0308_1` | D3,D2,D1 | não | `ra=10.6847&dec=41.2692&observation_id=2026W32_1A_0308_1&mode=rgb&size=2.0&upscale=1` |

## Nebulosa de Órion (`m42`)

_Núcleo saturado (fica com um furo). RGB com gradiente verde._

- Busca: `GET /epochs?ra=83.8221&dec=-5.3911` -> 70 observações, 5 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=83.822792, dec=-5.3915.
- Detector `single`: D3; visitas elegíveis: {'single': [2, 3, 4], 'rgb': [4]}; escolhidas: {'single': [2, 3, 4], 'rgb': [4]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 2 | 2026-09-14T05:42:07Z | `2026W38_1A_0049_1` | D3 | não | `ra=83.8221&dec=-5.3911&observation_id=2026W38_1A_0049_1&mode=single&size=1.0&upscale=1&detector=D3` |
| single | 3 | 2026-09-25T22:05:46Z | `2026W39_2A_0304_1` | D3 | sim | `ra=83.8221&dec=-5.3911&observation_id=2026W39_2A_0304_1&mode=single&size=1.0&upscale=1&detector=D3&scale_min=0.08784118503332138&scale_max=32.10864213943496` |
| single | 4 | 2026-10-01T10:01:40Z | `2026W40_1A_0767_1` | D3 | sim | `ra=83.8221&dec=-5.3911&observation_id=2026W40_1A_0767_1&mode=single&size=1.0&upscale=1&detector=D3&scale_min=0.08784118503332138&scale_max=32.10864213943496` |
| rgb | 4 | 2026-10-01T10:01:40Z | `2026W40_1A_0767_1` | D3,D2,D1 | não | `ra=83.8221&dec=-5.3911&observation_id=2026W40_1A_0767_1&mode=rgb&size=1.0&upscale=1` |

## Nebulosa do Caranguejo (`m1`)

_Pequena: ~7′._

- Busca: `GET /epochs?ra=83.6331&dec=22.0145` -> 52 observações, 1 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=83.633167, dec=22.015292.
- Detector `single`: D2; visitas elegíveis: {'single': [0], 'rgb': [0]}; escolhidas: {'single': [0], 'rgb': [0]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-09-12T19:42:50Z | `2026W37_2A_0487_1` | D2 | não | `ra=83.6331&dec=22.0145&observation_id=2026W37_2A_0487_1&mode=single&size=0.5&upscale=1&detector=D2` |
| rgb | 0 | 2026-09-11T12:45:12Z | `2026W37_2A_0218_1` | D3,D2,D1 | não | `ra=83.6331&dec=22.0145&observation_id=2026W37_2A_0218_1&mode=rgb&size=0.5&upscale=1` |

## Galáxia do Redemoinho (`m51`)

- Busca: `GET /epochs?ra=202.4696&dec=47.1953` -> 59 observações, 5 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=202.469958, dec=47.196125.
- Detector `single`: D2; visitas elegíveis: {'single': [0, 2, 3, 4], 'rgb': [0]}; escolhidas: {'single': [0, 3, 4], 'rgb': [0]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-05-16T05:35:49Z | `2026W20_2A_0275_1` | D2 | não | `ra=202.4696&dec=47.1953&observation_id=2026W20_2A_0275_1&mode=single&size=0.5&upscale=1&detector=D2` |
| single | 3 | 2026-06-07T18:35:41Z | `2026W23_2A_0607_1` | D2 | sim | `ra=202.4696&dec=47.1953&observation_id=2026W23_2A_0607_1&mode=single&size=0.5&upscale=1&detector=D2&scale_min=0.012321608187630773&scale_max=3.74199875831606` |
| single | 4 | 2026-06-19T10:55:27Z | `2026W25_2A_0201_1` | D2 | sim | `ra=202.4696&dec=47.1953&observation_id=2026W25_2A_0201_1&mode=single&size=0.5&upscale=1&detector=D2&scale_min=0.012321608187630773&scale_max=3.74199875831606` |
| rgb | 0 | 2026-05-15T14:57:22Z | `2026W20_2A_0183_1` | D3,D2,D1 | não | `ra=202.4696&dec=47.1953&observation_id=2026W20_2A_0183_1&mode=rgb&size=0.5&upscale=1` |

## Galáxia do Cata-vento (`m101`)

_Posição usada nos testes (observation_id 2026W20_2A_0464_3)._

- Busca: `GET /epochs?ra=210.8023&dec=54.349` -> 66 observações, 7 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=210.8015, dec=54.348917.
- Detector `single`: D2; visitas elegíveis: {'single': [0, 1, 2, 3, 4, 5, 6], 'rgb': [2, 5]}; escolhidas: {'single': [0, 3, 6], 'rgb': [2, 5]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-05-17T10:53:45Z | `2026W20_2A_0464_1` | D2 | não | `ra=210.8023&dec=54.349&observation_id=2026W20_2A_0464_1&mode=single&size=0.5&upscale=1&detector=D2` |
| single | 3 | 2026-06-06T08:19:42Z | `2026W23_2A_0336_1` | D2 | sim | `ra=210.8023&dec=54.349&observation_id=2026W23_2A_0336_1&mode=single&size=0.5&upscale=1&detector=D2&scale_min=0.004303843155503273&scale_max=1.770799088478092` |
| single | 6 | 2026-06-22T20:21:33Z | `2026W26_1A_0178_1` | D2 | sim | `ra=210.8023&dec=54.349&observation_id=2026W26_1A_0178_1&mode=single&size=0.5&upscale=1&detector=D2&scale_min=0.004303843155503273&scale_max=1.770799088478092` |
| rgb | 2 | 2026-05-30T23:08:02Z | `2026W22_2A_0431_1` | D3,D2,D1 | não | `ra=210.8023&dec=54.349&observation_id=2026W22_2A_0431_1&mode=rgb&size=0.5&upscale=1` |
| rgb | 5 | 2026-06-18T00:38:42Z | `2026W25_1A_0614_1` | D3,D2,D1 | sim | `ra=210.8023&dec=54.349&observation_id=2026W25_1A_0614_1&mode=rgb&size=0.5&upscale=1&scale_mins=0.002723423698917031%2C0.00614667572081089%2C0.0051260974630713465&scale_maxs=2.0276594901084772%2C1.5209007358550968%2C1.1907043361663818` |

## Nebulosa do Anel (`m57`)

_Muito pequena (~1′): poucos pixels de 6,15″._

- Busca: `GET /epochs?ra=283.3963&dec=33.0292` -> 63 observações, 5 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=283.397125, dec=33.028917.
- Detector `single`: D1; visitas elegíveis: {'single': [2, 3, 4], 'rgb': []}; escolhidas: {'single': [2, 3, 4], 'rgb': []}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 2 | 2026-09-19T11:57:57Z | `2026W38_2A_0414_4` | D1 | não | `ra=283.3963&dec=33.0292&observation_id=2026W38_2A_0414_4&mode=single&size=0.3&upscale=1&detector=D1` |
| single | 3 | 2026-09-27T13:42:30Z | `2026W39_2A_0643_1` | D1 | sim | `ra=283.3963&dec=33.0292&observation_id=2026W39_2A_0643_1&mode=single&size=0.3&upscale=1&detector=D1&scale_min=0.02893791552633047&scale_max=4.182323408126862` |
| single | 4 | 2026-09-29T16:10:26Z | `2026W40_1A_0370_1` | D1 | sim | `ra=283.3963&dec=33.0292&observation_id=2026W40_1A_0370_1&mode=single&size=0.3&upscale=1&detector=D1&scale_min=0.02893791552633047&scale_max=4.182323408126862` |
- ⚠️ rgb: rgb indisponível em todas as visitas

## Nebulosa do Haltere (`m27`)

_Pequena (~8′)._

- Busca: `GET /epochs?ra=299.9013&dec=22.7211` -> 34 observações, 4 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=299.901333, dec=22.720833.
- Detector `single`: D3; visitas elegíveis: {'single': [0, 1, 2, 3], 'rgb': []}; escolhidas: {'single': [0, 2, 3], 'rgb': []}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-06-03T08:18:56Z | `2026W23_1A_0416_3` | D3 | não | `ra=299.9013&dec=22.7211&observation_id=2026W23_1A_0416_3&mode=single&size=0.3&upscale=1&detector=D3` |
| single | 2 | 2026-09-26T14:57:08Z | `2026W39_2A_0454_1` | D3 | sim | `ra=299.9013&dec=22.7211&observation_id=2026W39_2A_0454_1&mode=single&size=0.3&upscale=1&detector=D3&scale_min=0.2308946917951107&scale_max=16.400424766540485` |
| single | 3 | 2026-09-29T11:22:21Z | `2026W40_1A_0326_1` | D3 | sim | `ra=299.9013&dec=22.7211&observation_id=2026W40_1A_0326_1&mode=single&size=0.3&upscale=1&detector=D3&scale_min=0.2308946917951107&scale_max=16.400424766540485` |
- ⚠️ rgb: rgb indisponível em todas as visitas

## Plêiades (`m45`)

_Grande (~2°). Estrelas brilhantes dominam._

- Busca: `GET /epochs?ra=56.85&dec=24.117` -> 56 observações, 1 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=56.849917, dec=24.116542.
- Detector `single`: D2; visitas elegíveis: {'single': [0], 'rgb': [0]}; escolhidas: {'single': [0], 'rgb': [0]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-08-20T19:25:36Z | `2026W34_2A_0062_1` | D2 | não | `ra=56.85&dec=24.117&observation_id=2026W34_2A_0062_1&mode=single&size=2.0&upscale=1&detector=D2` |
| rgb | 0 | 2026-08-17T08:24:29Z | `2026W34_1A_0070_1` | D3,D2,D1 | não | `ra=56.85&dec=24.117&observation_id=2026W34_1A_0070_1&mode=rgb&size=2.0&upscale=1` |

## Nebulosa da Águia (`m16`)

- Busca: `GET /epochs?ra=274.7&dec=-13.82` -> 83 observações, 2 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=274.7, dec=-13.820417.
- Detector `single`: D1; visitas elegíveis: {'single': [0, 1], 'rgb': [0]}; escolhidas: {'single': [0, 1], 'rgb': [0]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-08-31T08:38:27Z | `2026W36_1A_0082_1` | D1 | não | `ra=274.7&dec=-13.82&observation_id=2026W36_1A_0082_1&mode=single&size=0.75&upscale=1&detector=D1` |
| single | 1 | 2026-10-04T00:49:28Z | `2026W40_2A_0662_1` | D1 | sim | `ra=274.7&dec=-13.82&observation_id=2026W40_2A_0662_1&mode=single&size=0.75&upscale=1&detector=D1&scale_min=0.21590330302715302&scale_max=10.407723693847739` |
| rgb | 0 | 2026-08-25T22:19:14Z | `2026W35_1A_0408_1` | D3,D2,D1 | não | `ra=274.7&dec=-13.82&observation_id=2026W35_1A_0408_1&mode=rgb&size=0.75&upscale=1` |

## Nebulosa da Lagoa (`m8`)

- Busca: `GET /epochs?ra=270.904&dec=-24.387` -> 55 observações, 3 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=270.904083, dec=-24.386458.
- Detector `single`: D3; visitas elegíveis: {'single': [0, 2], 'rgb': [0]}; escolhidas: {'single': [0, 2], 'rgb': [0]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-08-27T02:07:10Z | `2026W35_1A_0641_1` | D3 | não | `ra=270.904&dec=-24.387&observation_id=2026W35_1A_0641_1&mode=single&size=1.0&upscale=1&detector=D3` |
| single | 2 | 2026-09-22T03:41:17Z | `2026W39_1A_0259_1` | D3 | sim | `ra=270.904&dec=-24.387&observation_id=2026W39_1A_0259_1&mode=single&size=1.0&upscale=1&detector=D3&scale_min=3.130773513317108&scale_max=42.07955116271974` |
| rgb | 0 | 2026-08-27T02:07:10Z | `2026W35_1A_0641_1` | D3,D2,D1 | não | `ra=270.904&dec=-24.387&observation_id=2026W35_1A_0641_1&mode=rgb&size=1.0&upscale=1` |

## Galáxia de Bode (`m81`)

- Busca: `GET /epochs?ra=148.8883&dec=69.0653` -> 0 observações, 0 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=148.888083, dec=69.0645.
- Detector `single`: None; visitas elegíveis: None; escolhidas: None.

- ⚠️ epochs: sem cobertura nesta posição

## Galáxia do Sombreiro (`m104`)

- Busca: `GET /epochs?ra=189.9975&dec=-11.6231` -> 58 observações, 4 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=189.997417, dec=-11.6235.
- Detector `single`: D2; visitas elegíveis: {'single': [0, 1, 3], 'rgb': [0]}; escolhidas: {'single': [0, 1, 3], 'rgb': [0]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-05-31T09:14:49Z | `2026W22_2A_0512_1` | D2 | não | `ra=189.9975&dec=-11.6231&observation_id=2026W22_2A_0512_1&mode=single&size=0.5&upscale=1&detector=D2` |
| single | 1 | 2026-06-20T03:20:00Z | `2026W25_2A_0357_2` | D2 | sim | `ra=189.9975&dec=-11.6231&observation_id=2026W25_2A_0357_2&mode=single&size=0.5&upscale=1&detector=D2&scale_min=0.013709733933210374&scale_max=5.5639006805417655` |
| single | 3 | 2026-07-09T08:30:46Z | `2026W28_1A_0861_1` | D2 | sim | `ra=189.9975&dec=-11.6231&observation_id=2026W28_1A_0861_1&mode=single&size=0.5&upscale=1&detector=D2&scale_min=0.013709733933210374&scale_max=5.5639006805417655` |
| rgb | 0 | 2026-05-29T14:52:32Z | `2026W22_2A_0189_1` | D3,D2,D1 | não | `ra=189.9975&dec=-11.6231&observation_id=2026W22_2A_0189_1&mode=rgb&size=0.5&upscale=1` |

## Centro Galáctico (Sgr A*) (`sgra`)

_Campo muito denso e brilhante._

- Busca: `GET /epochs?ra=266.4168&dec=-29.0078` -> 55 observações, 2 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=266.416292, dec=-29.0075.
- Detector `single`: D2; visitas elegíveis: {'single': [0, 1], 'rgb': [0]}; escolhidas: {'single': [0, 1], 'rgb': [0]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-08-26T11:28:04Z | `2026W35_1A_0523_1` | D2 | não | `ra=266.4168&dec=-29.0078&observation_id=2026W35_1A_0523_1&mode=single&size=1.0&upscale=1&detector=D2` |
| single | 1 | 2026-09-22T06:55:46Z | `2026W39_1A_0289_1` | D2 | sim | `ra=266.4168&dec=-29.0078&observation_id=2026W39_1A_0289_1&mode=single&size=1.0&upscale=1&detector=D2&scale_min=0.6822704410552979&scale_max=19.865628204345697` |
| rgb | 0 | 2026-08-25T01:16:30Z | `2026W35_1A_0207_1` | D3,D2,D1 | não | `ra=266.4168&dec=-29.0078&observation_id=2026W35_1A_0207_1&mode=rgb&size=1.0&upscale=1` |

## Nebulosa da Carina (`ngc3372`)

- Busca: `GET /epochs?ra=161.264&dec=-59.684` -> 81 observações, 8 visitas (coleção `spherex_qr3`).
- Posição normalizada pelo servidor: ra=161.26325, dec=-59.684042.
- Detector `single`: D3; visitas elegíveis: {'single': [0, 1, 2, 3, 4, 5, 6], 'rgb': [4]}; escolhidas: {'single': [0, 3, 6], 'rgb': [4]}.

| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | Query de `/image` |
|---|---|---|---|---|---|---|
| single | 0 | 2026-06-03T04:15:36Z | `2026W23_1A_0389_1` | D3 | não | `ra=161.264&dec=-59.684&observation_id=2026W23_1A_0389_1&mode=single&size=1.5&upscale=1&detector=D3` |
| single | 3 | 2026-06-15T16:00:12Z | `2026W25_1A_0124_1` | D3 | sim | `ra=161.264&dec=-59.684&observation_id=2026W25_1A_0124_1&mode=single&size=1.5&upscale=1&detector=D3&scale_min=0.5730208885669709&scale_max=23.30367677688597` |
| single | 6 | 2026-07-12T01:54:11Z | `2026W28_2A_0492_1` | D3 | sim | `ra=161.264&dec=-59.684&observation_id=2026W28_2A_0492_1&mode=single&size=1.5&upscale=1&detector=D3&scale_min=0.5730208885669709&scale_max=23.30367677688597` |
| rgb | 4 | 2026-06-21T05:41:03Z | `2026W25_2A_0592_1` | D3,D2,D1 | não | `ra=161.264&dec=-59.684&observation_id=2026W25_2A_0592_1&mode=rgb&size=1.5&upscale=1` |
