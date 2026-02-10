# Torre.ai AI-Powered Screening Process

Proof of Concept (POC) for an AI-powered screening workflow where candidates apply with Torre identifiers, complete a screening call with Emma, and receive a post-call fit analysis.

## Project Structure

- `apps/backend`: FastAPI entrypoint, HTTP routes, WebSocket route, API schemas
- `apps/frontend`: Vue 3 + Vite frontend (application, call, analysis pages)
- `src/screening`: Screening bounded context (applications, calls, analysis)
- `src/shared`: Shared domain primitives (events)
- `tests`: Unit and integration tests
- `docs`: PRD, API/WebSocket contract, architecture and scoring docs

## Architecture

The backend follows Hexagonal Architecture (Ports and Adapters) with DDD layering:

1. `domain`: entities, value objects, domain events
2. `application`: use-case orchestration and ports
3. `infrastructure`: adapters (Torre API, repositories, broker, Ollama)

## Core Flow

1. `POST /api/applications` receives `username` + `job_offer_id`
2. Backend fetches Torre bios/opportunity data and persists candidate/job/application
3. `JobOfferApplied` triggers prompt and embedding preparation
4. Candidate connects to `WS /api/ws/call?application_id=<uuid>`
5. On call completion, `CallFinished` triggers analysis generation
6. Frontend polls `GET /api/applications/{application_id}/analysis`

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose (optional, for full stack)

## Local Setup (without Docker)

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
python -m apps.backend
```

Backend: `http://localhost:8000`

### Frontend

```bash
cd apps/frontend
npm ci
npm run dev
```

Frontend: `http://localhost:5173`

### Try the flow

Open:

```text
http://localhost:5173/application?username=YOUR_TORRE_USERNAME&job_offer_id=YOUR_JOB_OFFER_ID
```

## Docker Compose

From repo root:

```bash
make up-d
```

Services:

- Frontend: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

Optional Ollama profile:

```bash
make up-ollama
```

Pull the required embedding model (one-time per Ollama data volume):

```bash
make ollama-pull-embed
```

Verify model is present:

```bash
make ollama-list-models
```

Ollama models are persisted in Docker volume `ollama_data`.

When running in Docker, backend defaults to `SCREENING_OLLAMA_BASE_URL=http://ollama:11434`.
Override if needed, for example:

```bash
SCREENING_OLLAMA_BASE_URL=http://host.docker.internal:11434 make up-d
```

Stop stack:

```bash
make down
```

## Configuration

Backend env vars use `SCREENING_` prefix (see `src/config.py`):

- `SCREENING_CORS_ORIGINS`
- `SCREENING_TORRE_BASE_URL`
- `SCREENING_TORRE_TIMEOUT`
- `SCREENING_TORRE_RETRIES`
- `SCREENING_DATABASE_URL`
- `SCREENING_BROKER_URL`
- `SCREENING_OLLAMA_BASE_URL`
- `SCREENING_OLLAMA_EMBED_MODEL`
- `SCREENING_OLLAMA_CHAT_MODEL`

Frontend env var:

- `VITE_API_BASE_URL` (default `http://localhost:8000`)

Ollama notes:

- `SCREENING_OLLAMA_EMBED_MODEL` defaults to `nomic-embed-text`
- the model must exist in the Ollama instance (for Docker profile: run `make ollama-pull-embed`)

## Testing

Backend tests:

```bash
source .venv/bin/activate
pytest
```

Frontend tests:

```bash
cd apps/frontend
npm run test
```

## Documentation

- `docs/prd-screening-simulation.md`
- `docs/api-websocket-contract.md`
- `docs/bounded-context-structure.md`
- `docs/fit-score-algorithm.md`
- `docs/torre-api-paths.md`
- `docs/design-specs/design-screening-frontend-phase1.md`
- `docs/design-specs/design-screening-backend-phase2.md`
- `docs/design-specs/design-screening-integration-phase3.md`

## Status

This project is a POC in active development.
