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
- Docker + Docker Compose (optional for local dev, required for EC2 stack)

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

## AWS EC2 Ready Setup (Default EC2 DNS + Nginx + Postgres)

This repository includes a low-cost EC2 deployment stack:
- `docker-compose.ec2.yml`
- `docker-compose.ec2.https.yml` (optional HTTPS override)
- `Dockerfile.nginx`
- `deploy/nginx/default.conf`
- `deploy/nginx/default-https.conf`
- `.env.ec2.example`

### 1) Create EC2 instance

- Launch one Ubuntu EC2 instance (`t4g.small` is the default low-cost profile in Terraform).
- Security group inbound:
  - `22` (SSH)
  - `80` (HTTP)
  - `443` (HTTPS, recommended for full call flow)

### 2) Install runtime dependencies on EC2

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git || sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Re-login to apply Docker group membership.

### 3) Deploy stack on EC2

```bash
git clone <your-repo-url> torre-screening
cd torre-screening
cp .env.ec2.example .env.ec2
```

Edit `.env.ec2` and set at least:
- `POSTGRES_PASSWORD` (required)
- `SCREENING_CORS_ORIGINS` (set to your EC2 URL origin)

Then run:

```bash
docker compose --env-file .env.ec2 -f docker-compose.ec2.yml up -d --build
```

Pull required Ollama models (one-time per EC2 volume):

```bash
make ec2-ollama-pull-embed
make ec2-ollama-pull-chat
```

Check status:

```bash
docker compose --env-file .env.ec2 -f docker-compose.ec2.yml ps
```

Open:

```text
http://<EC2_PUBLIC_DNS>/application?username=YOUR_TORRE_USERNAME&job_offer_id=YOUR_JOB_OFFER_ID
```

### HTTPS note for call/microphone

The call page checks secure context before requesting microphone access. On plain HTTP, browser microphone flow is blocked.

For full call functionality, enable HTTPS on Nginx (`443`) with a valid certificate.

HTTPS start command:

```bash
docker compose --env-file .env.ec2 -f docker-compose.ec2.yml -f docker-compose.ec2.https.yml up -d --build
```

Set in `.env.ec2`:
- `TLS_CERT_PATH=/absolute/path/to/fullchain.pem`
- `TLS_KEY_PATH=/absolute/path/to/privkey.pem`

## GitHub Actions CI/CD (EC2)

Workflow file: `.github/workflows/ec2-cicd.yml`

Execution model:
1. Runs backend unit tests and frontend tests.
2. Deploy job runs only on manual trigger (`workflow_dispatch`) and only when EC2 secrets are set.
3. Deploy uploads a release tarball to EC2 over SSH and runs:
   `docker compose --env-file .env.ec2 -f docker-compose.ec2.yml up -d --build`.

Required GitHub repository secrets:
- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`

Notes:
- The workflow expects `.env.ec2` to exist on EC2.
- On first deploy, if `.env.ec2` is missing, the job creates it from `.env.ec2.example` and exits so you can set real values.
- Recommended order: run Terraform first, then set secrets, then run deploy workflow manually.
- After first deploy, pull Ollama models once on EC2 (`make ec2-ollama-pull-embed` and `make ec2-ollama-pull-chat`).

## Terraform (Run First)

Minimal template location:
- `infra/terraform/ec2-minimal`

What it provisions:
- 1 EC2 Ubuntu instance
- 1 security group (`22`, `80`, `443`)

Quick start:

```bash
cd infra/terraform/ec2-minimal
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

Use output `public_dns` as:
- app URL base (`http://<public_dns>` or `https://<public_dns>` if TLS enabled)
- GitHub Actions secret `EC2_HOST`

Terraform now auto-selects Ubuntu AMI architecture from instance family:
- `t4g.*` -> `arm64`
- others (for example `t3a.*`) -> `amd64`

Terraform also auto-selects a default VPC subnet in an AZ that supports the chosen instance type (avoids unsupported-AZ errors for types like `t4g.small`).

Recommended sequence:
1. Provision EC2 with Terraform.
2. Use outputs to configure GitHub secrets (`EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`).
3. Prepare `.env.ec2` on EC2.
4. Run workflow `EC2 CI/CD` manually.

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

- `VITE_API_BASE_URL` (optional; default resolves to browser same-origin)

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
- `docs/aws-simple-deployment-schema.md`
- `docs/design-specs/design-screening-frontend-phase1.md`
- `docs/design-specs/design-screening-backend-phase2.md`
- `docs/design-specs/design-screening-integration-phase3.md`

## Status

This project is a POC in active development.
