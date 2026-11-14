"""Check the API over HTTP locally or after deployment."""

import argparse
import base64
import json
import sys
from datetime import datetime
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MAX_RESPONSE = 500 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def fetch(url, origin, timeout, *, method="GET", extra_headers=None):
    headers = {"Accept": "application/json", "Origin": origin, **(extra_headers or {})}
    request = Request(url, headers=headers, method=method)
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        body = response.read(MAX_RESPONSE + 1)
        check(len(body) <= MAX_RESPONSE, f"{url} excedeu 500 KiB")
        return response.status, response.headers, body


def parse(body):
    try:
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("resposta HTTP sem JSON válido") from error


def observation_time(frame):
    timestamp = datetime.fromisoformat(frame["observed_at_utc"].replace("Z", "+00:00"))
    check(timestamp.utcoffset() is not None, "data da observação sem fuso horário")
    return timestamp


def verify_live(base, args):
    ra, dec = args.field
    query = urlencode({"ra_deg": ra, "dec_deg": dec})
    for label in ("consulta", "repetição"):
        start = monotonic()
        status, headers, body = fetch(f"{base}/api/v1/sequence?{query}", args.origin, args.timeout)
        elapsed = monotonic() - start
        check(status == 200, f"{label}: HTTP {status}, {body[:250]!r}")
        check(headers.get("Access-Control-Allow-Origin") == args.origin, "CORS ausente na consulta")
        sequence = parse(body)
        frames = sequence["frames"]
        check(sequence["fov_arcmin"] == 6, "o campo precisa ter 6 minutos de arco")
        check(len(frames) == 2, "o visor precisa receber dois quadros")
        check(observation_time(frames[0]) < observation_time(frames[1]), "épocas fora de ordem")
        for frame in frames:
            source = frame["image_src"]
            prefix = "data:image/png;base64,"
            check(source.startswith(prefix), "quadro ao vivo sem PNG em data URL")
            png = base64.b64decode(source[len(prefix):], validate=True)
            check(png.startswith(PNG_SIGNATURE), "o quadro não possui assinatura PNG")
        cache = headers.get("X-Cache", "não informado")
        print(f"{label}: HTTP 200 em {elapsed:.2f} s ({len(body)} bytes), dois quadros, cache {cache}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True, help="URL base da API")
    parser.add_argument("--origin", required=True, help="origem web autorizada pela API")
    parser.add_argument("--timeout", type=float, default=100, help="segundos por requisição")
    parser.add_argument("--field", nargs=2, metavar=("RA", "DEC"), help="testar coordenadas no IRSA")
    args = parser.parse_args()
    base = args.api.rstrip("/")

    start = monotonic()
    status, headers, body = fetch(f"{base}/health", args.origin, args.timeout)
    check(status == 200 and parse(body).get("status") == "ok", f"/health: HTTP {status}, {body[:200]!r}")
    check(headers.get("Access-Control-Allow-Origin") == args.origin, "CORS ausente em /health")
    print(f"/health: HTTP 200 em {monotonic() - start:.2f} s")

    sequence_url = f"{base}/api/v1/sequence?ra_deg=360&dec_deg=0"
    status, headers, _ = fetch(
        sequence_url, args.origin, args.timeout, method="OPTIONS",
        extra_headers={"Access-Control-Request-Method": "GET"},
    )
    check(200 <= status < 300 and headers.get("Access-Control-Allow-Origin") == args.origin,
          f"preflight CORS falhou: HTTP {status}")
    status, headers, body = fetch(sequence_url, args.origin, args.timeout)
    check(status == 422 and parse(body).get("detail"), f"coordenada inválida: HTTP {status}")
    check(headers.get("Access-Control-Allow-Origin") == args.origin, "CORS ausente no erro 422")
    print("CORS e validação de coordenadas conferidos")

    if args.field:
        verify_live(base, args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, URLError, TimeoutError, KeyError, TypeError) as error:
        sys.exit(f"Falha na verificação: {error}")
