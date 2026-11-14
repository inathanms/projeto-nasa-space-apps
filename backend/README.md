# SPHEREx Sky Explorer — API

Minimal version: only `GET /health` (docs at `/docs`). See `../spec/spec-tool-spherex-image-api.md`.

Data: NASA/JPL-Caltech/IPAC — SPHEREx, via NASA/IPAC Infrared Science Archive (IRSA)

## Run locally

```bash
uv run uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health
```

## Docker

```bash
docker build -t spherex-api .
docker run -e PORT=9000 -p 9000:9000 spherex-api
```

## Deploy (Render)

New Web Service → Runtime: Docker, Root Directory: `backend`, Health Check Path: `/health`.
Render injects `PORT`. Set `CORS_ALLOWED_ORIGINS` to the frontend origin.
