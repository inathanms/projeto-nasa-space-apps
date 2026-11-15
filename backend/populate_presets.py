"""Popula o cache do SPHEREye com astros conhecidos (presets do frontend).

Para cada astro de `PRESETS` o script usa a API em execução (nada de atalhos internos, então as
chaves de cache são exatamente as que o frontend vai gerar):

1. `GET /epochs` na posição do astro -> visitas e observações disponíveis.
2. Escolhe algumas visitas (espaçadas no tempo, sempre incluindo a primeira e a última).
3. `GET /image?...&response_format=json` para cada visita e modo (`single` e/ou `rgb`).
   Com `json` o servidor só responde depois de gravar o PNG e o sidecar no bucket.

O IRSA responde 502/503/504 com frequência. Toda chamada é repetida com backoff exponencial e
jitter (`--max-attempts`, `--base-delay`, `--max-delay`); só o que esgota as tentativas é
registrado como falha. Reexecutar é barato: o que já está no cache volta como HIT em ~1 s, e com
`--resume` (padrão) os astros concluídos no manifesto são pulados.

Uso (com a API rodando e `CACHE_ENABLED=true`):

    uv run uvicorn app.main:app --port 8000          # em outro terminal
    uv run python populate_presets.py --dry-run       # mostra o plano, sem rede
    uv run python populate_presets.py                 # popula tudo
    uv run python populate_presets.py --only m31,m42 --modes single --max-visits 3

Saída (em `--out-dir`, padrão `presets_output/`):
    presets_manifest.json   detalhes da busca de cada astro, para montar a lista no site
    presets_manifest.md     o mesmo em tabelas legíveis

IMPORTANTE para o frontend: a chave de cache depende de TODOS os parâmetros (size, upscale,
stretch, colormap, percentis, escala...). O manifesto grava, para cada imagem, a query exata
usada (`image.query`). O frontend só terá HIT se pedir com os mesmos valores. Ele também mostra
o padrão "travar escala": a 1ª visita é pedida só com percentis, e as demais já com
`scale_min`/`scale_max` (ou `scale_mins`/`scale_maxs` no rgb) lidos do JSON da 1ª, igual ao
que o frontend faz para a imagem não "piscar" entre datas (desligue com `--no-lock-scale`).
Posições são normalizadas pelo servidor para a grade de 6,15″ (1 pixel nativo): `ra`/`dec`
dentro de meio pixel dos valores dos presets caem na mesma chave.

Detalhes de busca por astro (como a escolha é feita):
- Visita: `/epochs` agrupa observações da mesma região em sequência curta (VISIT_GAP_DAYS).
  Só entram visitas que servem ao modo (veja abaixo); entre elas, `--max-visits N` pega N
  igualmente espaçadas na linha do tempo (sempre a primeira e a última elegíveis).
- Detector (`single`): o detector que aparece em mais visitas do astro (empate: ordem
  D2, D3, D1, D5, D6, D4), para as datas serem comparáveis. Elegíveis: visitas que o têm; em
  cada uma usa-se a primeira observação com esse detector.
- `rgb`: elegíveis: visitas com `rgb_available`; usa a 1ª observação da visita como referência
  e os detectores padrão D3,D2,D1 (R,G,B).
- O manifesto registra, por modo, as visitas elegíveis e as escolhidas (`search`).
- `size` é por astro (graus, 0.01–3.0), ver `PRESETS`.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("presets")

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
DETECTOR_PREFERENCE = ("D2", "D3", "D1", "D5", "D6", "D4")


@dataclass(frozen=True)
class Preset:
    """Astro de preset. `ra`/`dec` em graus ICRS; `size` é o lado da imagem em graus."""

    id: str
    name: str
    catalog: str
    kind: str
    ra: float
    dec: float
    size: float
    note: str = ""


# Coordenadas ICRS (J2000) do centro de cada objeto. `size` cobre o objeto com folga.
PRESETS: tuple[Preset, ...] = (
    Preset(
        "m31",
        "Galáxia de Andrômeda",
        "M31 / NGC 224",
        "galáxia",
        10.6847,
        41.2692,
        2.0,
        "Grande: ~3° no céu. Núcleo muito brilhante.",
    ),
    Preset(
        "m42",
        "Nebulosa de Órion",
        "M42 / NGC 1976",
        "nebulosa",
        83.8221,
        -5.3911,
        1.0,
        "Núcleo saturado (fica com um furo). RGB com gradiente verde.",
    ),
    Preset(
        "m1",
        "Nebulosa do Caranguejo",
        "M1 / NGC 1952",
        "remanescente de supernova",
        83.6331,
        22.0145,
        0.5,
        "Pequena: ~7′.",
    ),
    Preset("m51", "Galáxia do Redemoinho", "M51 / NGC 5194", "galáxia", 202.4696, 47.1953, 0.5),
    Preset(
        "m101",
        "Galáxia do Cata-vento",
        "M101 / NGC 5457",
        "galáxia",
        210.8023,
        54.3490,
        0.5,
        "Posição usada nos testes (observation_id 2026W20_2A_0464_3).",
    ),
    Preset(
        "m57",
        "Nebulosa do Anel",
        "M57 / NGC 6720",
        "nebulosa planetária",
        283.3963,
        33.0292,
        0.3,
        "Muito pequena (~1′): poucos pixels de 6,15″.",
    ),
    Preset(
        "m27",
        "Nebulosa do Haltere",
        "M27 / NGC 6853",
        "nebulosa planetária",
        299.9013,
        22.7211,
        0.3,
        "Pequena (~8′).",
    ),
    Preset(
        "m45",
        "Plêiades",
        "M45",
        "aglomerado aberto",
        56.85,
        24.117,
        2.0,
        "Grande (~2°). Estrelas brilhantes dominam.",
    ),
    Preset("m16", "Nebulosa da Águia", "M16 / NGC 6611", "nebulosa", 274.70, -13.82, 0.75),
    Preset("m8", "Nebulosa da Lagoa", "M8 / NGC 6523", "nebulosa", 270.904, -24.387, 1.0),
    Preset("m81", "Galáxia de Bode", "M81 / NGC 3031", "galáxia", 148.8883, 69.0653, 0.75),
    Preset("m104", "Galáxia do Sombreiro", "M104 / NGC 4594", "galáxia", 189.9975, -11.6231, 0.5),
    Preset(
        "sgra",
        "Centro Galáctico (Sgr A*)",
        "Sgr A*",
        "centro galáctico",
        266.4168,
        -29.0078,
        1.0,
        "Campo muito denso e brilhante.",
    ),
    Preset("ngc3372", "Nebulosa da Carina", "NGC 3372", "nebulosa", 161.264, -59.684, 1.5),
)


class GiveUp(Exception):
    """Esgotou as tentativas em um erro transitório (502/503/504, timeout, rede)."""


class Permanent(Exception):
    """Erro definitivo da API (404/422...): não adianta repetir."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(f"HTTP {status} {code}: {message}")
        self.status = status
        self.code = code


class Retrying:
    """GET com retry/backoff para as falhas transitórias do IRSA."""

    def __init__(
        self, client: httpx.Client, max_attempts: int, base_delay: float, max_delay: float
    ) -> None:
        self.client = client
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def get(self, path: str, params: dict[str, Any], label: str) -> httpx.Response:
        reason = "?"
        for attempt in range(1, self.max_attempts + 1):
            try:
                resp = self.client.get(path, params=params)
            except httpx.TransportError as exc:  # inclui timeouts e conexão recusada
                reason = type(exc).__name__
            else:
                if resp.status_code == 200:
                    return resp
                if resp.status_code not in RETRYABLE_STATUS:
                    raise _permanent(resp)
                reason = f"HTTP {resp.status_code} {_error_code(resp)}"
            if attempt == self.max_attempts:
                raise GiveUp(f"{reason} (após {attempt} tentativas)")
            delay = min(self.max_delay, self.base_delay * 2 ** (attempt - 1))
            delay *= random.uniform(0.5, 1.0)  # jitter
            log.warning(
                "%s: %s, tentativa %d/%d, espera %.0fs",
                label,
                reason,
                attempt,
                self.max_attempts,
                delay,
            )
            time.sleep(delay)
        raise GiveUp(reason)  # inalcançável com max_attempts >= 1


def _error_code(resp: httpx.Response) -> str:
    try:
        return str(resp.json()["error"]["code"])
    except (ValueError, KeyError, TypeError):
        return ""


def _permanent(resp: httpx.Response) -> Permanent:
    try:
        err = resp.json()["error"]
        return Permanent(resp.status_code, err.get("code", ""), err.get("message", ""))
    except (ValueError, KeyError, TypeError, AttributeError):
        return Permanent(resp.status_code, "", resp.text[:200])


def pick_visits[T](visits: list[T], max_visits: int) -> list[T]:
    """Até `max_visits` itens igualmente espaçados, incluindo o primeiro e o último."""
    if max_visits <= 0 or len(visits) <= max_visits:
        return visits
    if max_visits == 1:
        return [visits[0]]
    last = len(visits) - 1
    idx = sorted({round(i * last / (max_visits - 1)) for i in range(max_visits)})
    return [visits[i] for i in idx]


def choose_detector(
    visits: list[dict[str, Any]], detectors_by_obs: dict[str, set[str]]
) -> str | None:
    """Detector presente no maior número de visitas (empate: DETECTOR_PREFERENCE)."""
    counts: Counter[str] = Counter()
    for visit in visits:
        in_visit: set[str] = set()
        for obs_id in visit["observation_ids"]:
            in_visit |= detectors_by_obs.get(obs_id, set())
        counts.update(in_visit)
    if not counts:
        return None
    return max(
        counts,
        key=lambda d: (
            counts[d],
            -DETECTOR_PREFERENCE.index(d) if d in DETECTOR_PREFERENCE else -99,
        ),
    )


def observation_with(
    visit: dict[str, Any], detector: str, detectors_by_obs: dict[str, set[str]]
) -> str | None:
    for obs_id in visit["observation_ids"]:
        if detector in detectors_by_obs.get(obs_id, set()):
            return obs_id
    return None


def _fmt(values: list[float]) -> str:
    return ",".join(repr(float(v)) for v in values)


def build_image_params(
    preset: Preset,
    mode: str,
    obs_id: str,
    detector: str | None,
    upscale: int,
    scale: dict[str, list[float]] | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "ra": preset.ra,
        "dec": preset.dec,
        "observation_id": obs_id,
        "mode": mode,
        "size": preset.size,
        "upscale": upscale,
        "response_format": "json",
    }
    if mode == "single":
        params["detector"] = detector
    if scale:
        if mode == "single":
            params["scale_min"], params["scale_max"] = scale["min"][0], scale["max"][0]
        else:
            params["scale_mins"], params["scale_maxs"] = _fmt(scale["min"]), _fmt(scale["max"])
    return params


def populate_preset(api: Retrying, preset: Preset, args: argparse.Namespace) -> dict[str, Any]:
    """Consulta `/epochs` e renderiza as imagens do astro. Nunca levanta: devolve o registro."""
    record: dict[str, Any] = {
        "id": preset.id,
        "name": preset.name,
        "catalog": preset.catalog,
        "kind": preset.kind,
        "ra": preset.ra,
        "dec": preset.dec,
        "size": preset.size,
        "note": preset.note,
        "images": [],
        "errors": [],
        "status": "done",
    }
    epochs_params: dict[str, Any] = {"ra": preset.ra, "dec": preset.dec}
    if args.collection:
        epochs_params["collection"] = args.collection
    try:
        epochs = api.get("/epochs", epochs_params, f"{preset.id} /epochs").json()
    except (GiveUp, Permanent) as exc:
        record["errors"].append({"step": "epochs", "error": str(exc)})
        record["status"] = "failed"
        return record

    visits: list[dict[str, Any]] = epochs["visits"]
    detectors_by_obs = {
        o["observation_id"]: {d["detector"] for d in o["detectors"]} for o in epochs["observations"]
    }
    record["search"] = {
        "epochs_query": epochs_params,
        "normalized_ra": epochs["query"]["ra"],
        "normalized_dec": epochs["query"]["dec"],
        "collection": epochs["query"]["collection"],
        "total_observations": epochs["total_observations"],
        "total_visits": epochs["total_visits"],
        "truncated": epochs["truncated"],
    }
    if not visits:
        record["errors"].append({"step": "epochs", "error": "sem cobertura nesta posição"})
        record["status"] = "no_coverage"
        return record

    detector = choose_detector(visits, detectors_by_obs)
    # Por modo: só visitas que servem (detector presente / rgb disponível), depois espaçadas.
    eligible: dict[str, list[tuple[dict[str, Any], str]]] = {"single": [], "rgb": []}
    for visit in visits:
        obs_single = detector and observation_with(visit, detector, detectors_by_obs)
        if obs_single:
            eligible["single"].append((visit, obs_single))
        if visit["rgb_available"]:
            eligible["rgb"].append((visit, visit["observation_ids"][0]))
    plan = {m: pick_visits(eligible[m], args.max_visits) for m in args.modes}
    record["search"]["single_detector"] = detector
    record["search"]["eligible_visits"] = {
        m: [v["visit_index"] for v, _ in eligible[m]] for m in args.modes
    }
    record["search"]["selected_visit_indexes"] = {
        m: [v["visit_index"] for v, _ in plan[m]] for m in args.modes
    }

    for mode in args.modes:
        scale: dict[str, list[float]] | None = None  # escala da 1ª imagem do modo
        if not plan[mode]:
            reason = (
                f"detector {detector} ausente em todas as visitas"
                if mode == "single"
                else ("rgb indisponível em todas as visitas")
            )
            record["errors"].append(
                {"step": "image", "mode": mode, "error": reason, "permanent": True}
            )
            continue
        for visit, obs_id in plan[mode]:
            params = build_image_params(
                preset,
                mode,
                obs_id,
                detector,
                args.upscale,
                scale if args.lock_scale else None,
            )
            label = f"{preset.id} {mode} visita {visit['visit_index']}"
            try:
                meta = api.get("/image", params, label).json()
            except Permanent as exc:
                log.error("%s: %s", label, exc)
                record["errors"].append(
                    {
                        "step": "image",
                        "mode": mode,
                        "visit_index": visit["visit_index"],
                        "error": str(exc),
                        "permanent": True,
                    }
                )
                continue
            except GiveUp as exc:
                log.error("%s: desistiu: %s", label, exc)
                record["errors"].append(
                    {
                        "step": "image",
                        "mode": mode,
                        "visit_index": visit["visit_index"],
                        "error": str(exc),
                        "permanent": False,
                    }
                )
                record["status"] = "partial"
                continue
            if meta["cache_status"] == "bypass" and not args.allow_bypass:
                raise SystemExit("o servidor respondeu BYPASS: o cache não está ativo.")
            if scale is None:
                scale = meta["scale"]
            log.info("%s: %s (%s)", label, meta["cache_status"].upper(), obs_id)
            record["images"].append(
                {
                    "mode": mode,
                    "visit_index": visit["visit_index"],
                    "visit_start_time": visit["start_time"],
                    "observation_id": obs_id,
                    "detectors": meta["observation"]["detectors"],
                    "wavelength_min_um": meta["observation"]["wavelength_min_um"],
                    "wavelength_max_um": meta["observation"]["wavelength_max_um"],
                    "observation_time": meta["observation"]["observation_time"],
                    "cache_status": meta["cache_status"],
                    "url": meta["url"],
                    "key": meta["key"],
                    "scale": meta["scale"],
                    "width": meta["image"]["width"],
                    "height": meta["image"]["height"],
                    "valid_pixel_fraction": meta["image"]["valid_pixel_fraction"],
                    "scale_locked": bool(
                        args.lock_scale and params.keys() & {"scale_min", "scale_mins"}
                    ),
                    "query": str(
                        httpx.QueryParams(
                            {k: v for k, v in params.items() if k != "response_format"}
                        )
                    ),
                }
            )
    if not record["images"] and record["status"] == "done":
        record["status"] = "no_images"
    return record


def write_outputs(out_dir: Path, manifest: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "presets_manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out_dir / "presets_manifest.json")
    (out_dir / "presets_manifest.md").write_text(render_markdown(manifest), encoding="utf-8")


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Presets do SPHEREye",
        "",
        (
            f"Gerado em {manifest['generated_at']} contra `{manifest['api']}`. "
            "Dados: NASA/JPL-Caltech/IPAC — SPHEREx, via IRSA."
        ),
        "",
        (
            "A chave de cache depende de todos os parâmetros: para ter HIT, o frontend deve "
            "usar a `query` exata de cada imagem (ou os mesmos valores)."
        ),
        "",
        "| Astro | Catálogo | Tipo | RA | Dec | Size (°) | Visitas | Imagens | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in manifest["presets"]:
        s = p.get("search", {})
        lines.append(
            f"| {p['name']} (`{p['id']}`) | {p['catalog']} | {p['kind']} | {p['ra']} | "
            f"{p['dec']} | {p['size']} | {s.get('total_visits', '-')} | {len(p['images'])} | "
            f"{p['status']} |"
        )
    for p in manifest["presets"]:
        lines += ["", f"## {p['name']} (`{p['id']}`)", ""]
        if p.get("note"):
            lines += [f"_{p['note']}_", ""]
        s = p.get("search")
        if s:
            lines += [
                (
                    f"- Busca: `GET /epochs?{httpx.QueryParams(s['epochs_query'])}` -> "
                    f"{s['total_observations']} observações, {s['total_visits']} visitas "
                    f"(coleção `{s['collection']}`)."
                ),
                (
                    f"- Posição normalizada pelo servidor: ra={s['normalized_ra']}, "
                    f"dec={s['normalized_dec']}."
                ),
                (
                    f"- Detector `single`: {s.get('single_detector')}; visitas elegíveis: "
                    f"{s.get('eligible_visits')}; escolhidas: {s.get('selected_visit_indexes')}."
                ),
                "",
            ]
        if p["images"]:
            lines += [
                (
                    "| Modo | Visita | Data (UTC) | Observação | Detectores | Escala travada | "
                    "Query de `/image` |"
                ),
                "|---|---|---|---|---|---|---|",
            ]
            for im in p["images"]:
                lines.append(
                    f"| {im['mode']} | {im['visit_index']} | {im['observation_time']} | "
                    f"`{im['observation_id']}` | {','.join(im['detectors'])} | "
                    f"{'sim' if im['scale_locked'] else 'não'} | `{im['query']}` |"
                )
        for err in p["errors"]:
            lines.append(f"- ⚠️ {err.get('mode', err['step'])}: {err['error']}")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--api", default="http://localhost:8000", help="URL base da API")
    ap.add_argument("--collection", help="coleção SIA (padrão: a do servidor)")
    ap.add_argument("--only", help="ids separados por vírgula (ex.: m31,m42)")
    ap.add_argument("--modes", default="single,rgb", help="single, rgb ou single,rgb")
    ap.add_argument("--max-visits", type=int, default=6, help="visitas por astro (0 = todas)")
    ap.add_argument("--upscale", type=int, default=1, choices=range(1, 5))
    ap.add_argument(
        "--no-lock-scale",
        dest="lock_scale",
        action="store_false",
        help="não reutiliza a escala da 1ª imagem nas demais datas",
    )
    ap.add_argument("--workers", type=int, default=2, help="astros em paralelo")
    ap.add_argument("--max-attempts", type=int, default=8, help="tentativas por chamada")
    ap.add_argument("--base-delay", type=float, default=5.0, help="backoff inicial, s")
    ap.add_argument("--max-delay", type=float, default=90.0, help="teto do backoff, s")
    ap.add_argument("--timeout", type=float, default=240.0, help="timeout por chamada, s")
    ap.add_argument("--out-dir", type=Path, default=Path("presets_output"))
    ap.add_argument("--force", action="store_true", help="refaz também os astros já concluídos")
    ap.add_argument("--allow-bypass", action="store_true", help="aceita servidor com cache off")
    ap.add_argument("--dry-run", action="store_true", help="só mostra o plano (sem rede)")
    args = ap.parse_args(argv)
    args.modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    if not set(args.modes) <= {"single", "rgb"} or not args.modes:
        ap.error("--modes aceita apenas single e/ou rgb")
    if args.max_attempts < 1:
        ap.error("--max-attempts deve ser >= 1")
    return args


def select_presets(only: str | None) -> list[Preset]:
    if not only:
        return list(PRESETS)
    wanted = [s.strip() for s in only.split(",") if s.strip()]
    known = {p.id: p for p in PRESETS}
    unknown = [w for w in wanted if w not in known]
    if unknown:
        raise SystemExit(f"ids desconhecidos: {', '.join(unknown)}. Válidos: {', '.join(known)}")
    return [known[w] for w in wanted]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"
    )
    presets = select_presets(args.only)

    if args.dry_run:
        print(f"API: {args.api} | modos: {','.join(args.modes)} | max_visits: {args.max_visits}")
        for p in presets:
            print(f"- {p.id:8} {p.name:30} ra={p.ra:<9} dec={p.dec:<9} size={p.size}")
        print(
            f"{len(presets)} astros; até {len(presets) * args.max_visits * len(args.modes)} "
            "imagens (+1 /epochs por astro)."
        )
        return 0

    manifest_path = args.out_dir / "presets_manifest.json"
    previous: dict[str, dict[str, Any]] = {}
    if manifest_path.exists() and not args.force:
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        previous = {p["id"]: p for p in old.get("presets", [])}

    client = httpx.Client(
        base_url=args.api,
        timeout=args.timeout,
        headers={"User-Agent": "sphereye-populate-presets/1.0"},
    )
    try:
        health = client.get("/health").json()
    except httpx.HTTPError as exc:
        print(f"API inacessível em {args.api}: {exc}", file=sys.stderr)
        return 2
    if not health["cache"]["enabled"] and not args.allow_bypass:
        print(
            "O servidor está com o cache desligado (CACHE_ENABLED=false); nada seria "
            "gravado. Use --allow-bypass para rodar mesmo assim.",
            file=sys.stderr,
        )
        return 2

    api = Retrying(client, args.max_attempts, args.base_delay, args.max_delay)
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "api": args.api,
        "params": {
            "modes": args.modes,
            "max_visits": args.max_visits,
            "upscale": args.upscale,
            "lock_scale": args.lock_scale,
            "collection": args.collection,
        },
        "presets": [],
    }
    results: dict[str, dict[str, Any]] = {}
    lock = threading.Lock()

    def flush() -> None:
        ordered = [results.get(p.id) or previous.get(p.id) for p in PRESETS]
        manifest["presets"] = [r for r in ordered if r]
        write_outputs(args.out_dir, manifest)

    todo = [p for p in presets if previous.get(p.id, {}).get("status") != "done"]
    for p in presets:
        if p not in todo:
            log.info("%s: já concluído no manifesto (use --force para refazer)", p.id)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(populate_preset, api, p, args): p for p in todo}
        for fut in as_completed(futures):
            preset = futures[fut]
            rec = fut.result()
            with lock:
                results[preset.id] = rec
                flush()
            log.info(
                "== %s: %s (%d imagens, %d erros)",
                preset.id,
                rec["status"],
                len(rec["images"]),
                len(rec["errors"]),
            )
    with lock:
        flush()

    final = {p.id: results.get(p.id) or previous.get(p.id) for p in presets}
    bad = [i for i, r in final.items() if not r or r["status"] in {"failed", "partial"}]
    print(f"\nConcluído em {time.monotonic() - started:.0f}s. Manifesto: {manifest_path}")
    if bad:
        print(f"Incompletos (rode de novo para repetir): {', '.join(bad)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
