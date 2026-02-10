# Design Document: Screening Backend — Phase 2

## Metadata

- **Related PRD**: [PRD: Screening Simulation (POC)](../prd-screening-simulation.md)
- **Phase**: Phase 2 — Backend: Services, Call Flow
- **Status**: Draft
- **Last Updated**: 2025-02-02
- **Author**: TBD
- **Reviewers**: TBD

---

## Overview

This design doc specifies the backend for the Screening Simulation POC: application service with Torre API integration, event publishing and subscribers (embeddings, call prompt), WebSocket-based call flow with Emma, and post-call analysis. The backend enables the full screening flow to be executed and tested via API and WebSocket without requiring the frontend. It aligns with the bounded context structure in [bounded-context-structure.md](../bounded-context-structure.md) (applications, calls, analysis modules) and uses domain events for module communication.

---

## Context

- **Problem**: The frontend (Phase 1) uses mock data. To run a real screening flow, the system needs APIs to create applications from Torre data, persistence, event-driven preparation (embeddings, call prompt), a WebSocket call with Emma (Q&A, role-only answers), and analysis when the call ends.
- **Goals**: (1) Expose application creation endpoint that fetches Torre APIs, persists candidate and job offer, and publishes `JobOfferApplied`. (2) Run event subscribers on `JobOfferApplied` to generate embeddings and call prompt. (3) Provide WebSocket call flow: Emma greeting → wait for candidate → Q&A with prepared questions; Emma answers candidate questions from role/job data only; Emma goodbye and close; publish `CallFinished`. (4) On `CallFinished`, run analysis (fit score, skills) and persist for the analysis page.
- **Scope**: In scope — application service and Torre adapters; event publishing (e.g. RabbitMQ); embedding and call-prompt subscribers; call/Emma service and WebSocket handler; analysis service and persistence. Out of scope — Phase 3 frontend integration; auth; video; advanced RAG beyond job/role context.

---

## Functional Specifications

### Feature 1: Application Service and Torre Integration

**Description**: HTTP endpoint that accepts `username` and `job_offer_id`, calls Torre public APIs to fetch candidate and job offer data, extracts required fields, persists candidate and job offer, publishes `JobOfferApplied`, and returns `application_id`. On Torre API or validation errors, returns an error so the frontend can show "not found."

**User story**: US2.1 — As the system, I want to fetch candidate and job data from Torre APIs and persist them so that the call and analysis can use them.

**Acceptance criteria** (from PRD):

- Given `username` and `job_offer_id`, when the application endpoint is called, the backend calls Torre genome/bios and opportunities APIs, extracts full name/skills/jobs and objective/strengths/responsibilities, and persists.
- When an API returns an error, the backend returns an error and the frontend can show "not found."

**Functional requirements**:

- FR-1.1: The system SHALL expose an HTTP endpoint `POST /api/applications` that accepts `username` and `job_offer_id` in the request body.
- FR-1.2: The system SHALL call `GET https://torre.ai/api/genome/bios/<username>` to fetch candidate data.
- FR-1.3: The system SHALL call `GET https://torre.ai/api/suite/opportunities/<job_offer_id>` to fetch job offer data. (PRD says "suite/opportunities"; Torre public API may use "opportunities" — align with actual Torre API path.)
- FR-1.4: The system SHALL extract from the candidate response: full name, skills (or strengths), and jobs (as needed for call/analysis).
- FR-1.5: The system SHALL extract from the job offer response: objective, strengths, and responsibilities (e.g. from details content).
- FR-1.6: The system SHALL persist the candidate and job offer in the project database and create an application record linking them, returning a stable `application_id`.
- FR-1.7: The system SHALL publish a `JobOfferApplied` domain event containing DB `candidate_id`, `job_offer_id`, and `application_id` after successful persistence.
- FR-1.8: The system SHALL return a non-2xx response with a clear error when Torre APIs return an error, when username/job_offer_id are missing or invalid, or when persistence fails, so the frontend can show "not found" or an error state.

**User flows**:

1. Client sends `POST /api/applications` with `{ "username": "johndoe", "job_offer_id": "abc123" }`.
2. Backend fetches Torre bios and opportunities; parses and validates responses.
3. Backend persists candidate, job offer, and application; publishes `JobOfferApplied`.
4. Backend returns `201` with `{ "application_id": "uuid" }`.
5. Alternative: Torre returns 404 or invalid data → return 404 or 422 with error payload; no event published.

**Edge cases**:

- Torre API timeout or 5xx: Retry once (configurable); then return 502/503 and do not persist.
- Malformed Torre response (missing expected fields): Map to sensible defaults where possible; if critical data missing, return 422 and do not persist.
- Duplicate application (same username + job_offer_id): Per API contract (see Technical Design): idempotent return 201 with existing `application_id`; no duplicate record created.
- Empty or invalid `username` / `job_offer_id`: Validate before calling Torre; return 400 with validation message.

---

### Feature 2: Event Subscribers (Embeddings and Call Prompt)

**Description**: On `JobOfferApplied`, three subscribers run: GenerateCandidateEmbeddings, GenerateJobOfferEmbeddings, and GenerateCallPrompt. They produce embeddings for candidate and job offer (for later analysis) and a call template with prepared questions for Emma.

**User story**: US2.2 — As the system, I want to publish `JobOfferApplied` and run embedding and call-prompt generation so that the call has prepared questions and embeddings.

**Acceptance criteria** (from PRD):

- Given a new application has been persisted, when `JobOfferApplied` is published (with DB candidate_id and job_offer_id), subscribers run GenerateCandidateEmbeddings, GenerateJobOfferEmbeddings, and GenerateCallPrompt.

**Functional requirements**:

- FR-2.1: The system SHALL subscribe to `JobOfferApplied` and invoke an embedding pipeline for the candidate (e.g. from bio/skills/jobs text) and persist or associate embeddings with the candidate.
- FR-2.2: The system SHALL subscribe to `JobOfferApplied` and invoke an embedding pipeline for the job offer (e.g. from objective/strengths/responsibilities) and persist or associate embeddings with the job offer.
- FR-2.3: The system SHALL subscribe to `JobOfferApplied` and generate a call prompt (template with prepared questions for Emma) from job offer and optionally candidate context, and persist or associate it with the application/call.
- FR-2.4: Subscribers SHALL be decoupled from the application service (event-driven); failure in one subscriber SHALL NOT block the others (e.g. independent consumption or retry).

**User flows**:

1. Application service publishes `JobOfferApplied` (candidate_id, job_offer_id, application_id).
2. Message broker delivers event to three subscribers (order not required).
3. GenerateCandidateEmbeddings: fetch candidate text, call embeddings provider, store result.
4. GenerateJobOfferEmbeddings: fetch job offer text, call embeddings provider, store result.
5. GenerateCallPrompt: build list of prepared questions (and role context) from job/candidate, store template for the call.

**Edge cases**:

- Embeddings provider unavailable: Retry with backoff; after max retries, dead-letter or log for manual replay; do not block call start (call can use non-embedding prompt).
- Call prompt generation failure: Retry; if persistent failure, call could fall back to a minimal default prompt so the call can still start.
- Event published but broker down: Per NFR (Reliability): publish is synchronous before responding; if broker is down, application request fails (e.g. 503); no best-effort fire-and-forget.

---

### Feature 3: Call Flow (WebSocket and Emma)

**Description**: WebSocket endpoint for the screening call. Emma greets the candidate, waits for a short response (e.g. 5s), runs a Q&A loop using prepared questions; when the candidate asks a question about the role, Emma answers using only job/role data. When all questions are done, Emma says goodbye and closes the call; WebSocket closes and `CallFinished` is published.

**User story**: US2.3 — As the system, I want a WebSocket call flow where Emma asks prepared questions and answers only role-related questions so that screening is consistent.

**Acceptance criteria** (from PRD):

- Given a call has started, when the WebSocket is open, Emma greets, waits for candidate response (e.g. 5s), then runs a Q&A loop with prepared questions.
- When the candidate asks a question about the role, Emma answers using job/role data only.
- When all questions are done, Emma says goodbye and the WebSocket closes.

**Functional requirements**:

- FR-3.1: The system SHALL expose a WebSocket endpoint `/api/ws/call` that accepts a connection keyed by `application_id` (query param `application_id` required).
- FR-3.2: The system SHALL load the call prompt (prepared questions and role context) for the application; if not ready, SHALL wait briefly or use a default minimal prompt.
- FR-3.3: The system SHALL play or send Emma’s greeting (audio or control message) upon call start.
- FR-3.4: The system SHALL wait for candidate response (e.g. up to 5s) after the greeting before proceeding to the first question.
- FR-3.5: The system SHALL run a Q&A loop: Emma asks the next prepared question; candidate responds; repeat until no more questions.
- FR-3.6: When the candidate asks a question about the role (detected by intent or keyword), Emma SHALL answer using only job/role data (objective, strengths, responsibilities); Emma SHALL NOT invent information outside that context.
- FR-3.7: The system SHALL support audio streaming (candidate → server, server → client for Emma) over the WebSocket or a defined protocol (e.g. base64 audio chunks, or separate media channel).
- FR-3.8: When all questions are completed, the system SHALL have Emma say goodbye and then close the WebSocket and publish `CallFinished` (with application_id / call_id) so that analysis can run.

**User flows**:

1. Client opens WebSocket with `application_id`.
2. Server loads prompt; sends greeting; waits ~5s for candidate.
3. Server sends first question; candidate answers (STT → text → optional LLM summarization); server sends next question; repeat.
4. If candidate asks "What does the role involve?", server uses job/role context only to generate Emma’s answer and streams it.
5. After last question, Emma says goodbye; server closes WebSocket and publishes `CallFinished`.

**Edge cases**:

- Call prompt not ready: Timeout after N seconds and use default short prompt (e.g. one generic question) so the call can proceed.
- Candidate disconnects mid-call: Close WebSocket, publish `CallFinished` so analysis can run with partial data; analysis handles incomplete transcript.
- Emma LLM/voice slow: Design for streaming and timeouts; consider short TTS chunks. POC may use Ollama; document latency expectations.
- Multiple tabs connecting for same application_id: Per API contract: only one active call per application_id; a new connection for the same application_id is rejected with close code **4409** so the existing call is not disrupted.

---

### Feature 4: Post-Call Analysis

**Description**: A subscriber listens for `CallFinished`. It runs analysis (fit score, skills extraction) using call transcript and stored candidate/job data (and embeddings if available), then persists the result so the analysis page can fetch and display it.

**User story**: US2.4 — As the system, I want to run analysis when the call ends and store the result so that the analysis page can show the score.

**Acceptance criteria** (from PRD):

- Given the WebSocket has closed, when `CallFinished` is published, a subscriber runs the analysis (fit score, skills) and persists the result for the given application.

**Functional requirements**:

- FR-4.1: The system SHALL subscribe to `CallFinished` (payload includes application_id or call_id).
- FR-4.2: The subscriber SHALL load the call transcript (stored as list of `TranscriptSegment`: speaker, text, timestamp) and associated candidate and job offer data (and embeddings if used).
- FR-4.3: The system SHALL compute a fit score (e.g. 0–100) and a list of skills (or strengths) relevant to the job, using a defined algorithm (e.g. embedding similarity + rules, or LLM-based summary).
- FR-4.4: The system SHALL persist the analysis result (fit score, skills) linked to the application so that a GET analysis endpoint can return it.
- FR-4.5: The system SHALL expose an HTTP endpoint `GET /api/applications/{application_id}/analysis` that returns the analysis when ready, or 202/404 while pending.

**User flows**:

1. Call service closes WebSocket and publishes `CallFinished(application_id)`.
2. Analysis subscriber receives event; loads transcript, candidate, job offer.
3. Subscriber runs fit score and skills logic; persists `ScreeningAnalysis` (or equivalent).
4. Client polls or fetches `GET /api/applications/<id>/analysis`; once ready, returns `{ fit_score, skills }`.

**Traceability — AnalysisCompleted**: The bounded context (Module Communication) states that the analysis module publishes `AnalysisCompleted` → "enables results display." For Phase 2, the analysis module does **not** publish `AnalysisCompleted`. Results are consumed by the client polling `GET /api/applications/{application_id}/analysis`. Phase 3 may introduce `AnalysisCompleted` (e.g. for push/SSE or future consumers); if added, document who consumes it.

**Edge cases**:

- Transcript empty or very short: Still persist analysis with a default/low fit score and empty or minimal skills; do not fail the pipeline.
- Analysis computation failure: Retry with backoff; after max retries, persist an error state or "analysis failed" so the frontend can show a message instead of endless loading.
- Duplicate `CallFinished` (at-least-once delivery): Idempotent analysis write (e.g. upsert by application_id) so re-delivery does not corrupt data.

---

## Technical Design

### Architecture

- **Stack**: Python, FastAPI (HTTP + WebSocket), Postgres (persistence), RabbitMQ (or equivalent) for domain events, Ollama (or configured LLM) for Emma, and an embeddings provider (e.g. OpenRouter or local model). Architecture is hexagonal and event-driven; modules are applications, calls, analysis per [bounded-context-structure.md](../bounded-context-structure.md).
- **Flow**: HTTP creates application → persist → publish `JobOfferApplied` → subscribers (embeddings, call prompt) run asynchronously. Client opens WebSocket for call → Emma runs Q&A → on close publish `CallFinished` → analysis subscriber runs → result persisted; client fetches analysis via HTTP.

```text
┌─────────────┐     POST /api/applications   ┌──────────────────┐
│   Client    │ ──────────────────────────► │ Application      │
│             │     username, job_offer_id   │ Service          │
└─────────────┘                              └────────┬─────────┘
       │                                              │ persist
       │                                              │ publish JobOfferApplied
       │                                              ▼
       │                              ┌───────────────────────────────┐
       │                              │ Message Broker (e.g. RabbitMQ) │
       │                              └───────┬───────────┬───────────┘
       │                                      │           │
       │                    ┌─────────────────┼───────────┼─────────────────┐
       │                    ▼                 ▼           ▼                   │
       │            GenerateCandidate   GenerateJob   GenerateCallPrompt     │
       │            Embeddings          Embeddings    (prepared questions)    │
       │                    │                 │           │                   │
       │                    └─────────────────┴───────────┘                   │
       │                                              │                       │
       │  WebSocket /api/ws/call?application_id=...   │                       │
       │ ─────────────────────────────────────────►  │  Call / Emma Service   │
       │  audio + control                             │  (Q&A, goodbye)       │
       │                                              │  on close: CallFinished
       │                                              ▼                       │
       │                              ┌───────────────────────────────┐     │
       │                              │ Broker                         │     │
       │                              └───────────┬─────────────────────┘     │
       │                                          │                           │
       │                                          ▼                           │
       │                              ┌───────────────────────────────┐     │
       │                              │ Analysis Subscriber            │     │
       │                              │ (fit score, skills, persist)   │     │
       │                              └───────────┬─────────────────────┘     │
       │                                          │                           │
       │  GET /api/applications/<id>/analysis      │                           │
       │ ◄────────────────────────────────────────┘                           │
       │  { fit_score, skills }                                                │
```

### Components

| Component | Module | Responsibility |
| --------- |--------|----------------|
| ApplicationService | applications | Create application: validate input, call Torre adapters, persist candidate/job/application, publish `JobOfferApplied`. |
| TorreBiosAdapter | applications (infra) | HTTP client for `GET torre.ai/api/genome/bios/<username>`; map response to domain DTO. |
| TorreOpportunitiesAdapter | applications (infra) | HTTP client for `GET torre.ai/api/suite/opportunities/<job_offer_id>`; map response to domain DTO. |
| EventPublisher | applications (port) | Publish domain events (e.g. to RabbitMQ). |
| JobOfferAppliedSubscribers | applications / shared | GenerateCandidateEmbeddings, GenerateJobOfferEmbeddings, GenerateCallPrompt; invoked by broker. |
| CallService | calls | Validate application_id, load call prompt, manage call lifecycle, publish `CallFinished` on close. |
| EmmaService | calls | Orchestrate greeting, wait, Q&A loop, role-only answers, goodbye; use LLM and TTS/STT adapters. |
| WebSocketHandler | calls (infra) | Accept WebSocket, parse application_id, delegate to CallService/EmmaService; handle audio stream. |
| LLMAdapter (e.g. Ollama) | calls (infra) | Generate Emma replies and optional role Q&A. |
| STT/TTS Adapters | calls (infra) | Speech-to-text (candidate), text-to-speech (Emma); POC may use Ollama or external provider. |
| AnalysisService | analysis | On `CallFinished`, load transcript and data, compute fit score and skills, persist result. |
| AnalysisRepository | analysis (infra) | Persist and retrieve analysis by application_id. |
| GET Analysis endpoint | analysis | Return analysis JSON or 202/404 when pending. |

### Data Models

Domain entities and value objects; persistence models can map from these.

```python
# applications module
@dataclass
class ScreeningApplication:
    id: ApplicationId
    candidate_id: CandidateId
    job_offer_id: JobOfferId
    created_at: datetime

@dataclass
class Candidate:
    id: CandidateId
    username: str
    full_name: str
    skills: list[str]  # or strengths
    jobs: list[dict]   # minimal for context

@dataclass
class JobOffer:
    id: JobOfferId
    external_id: str
    objective: str
    strengths: list[str]
    responsibilities: list[str]

class JobOfferApplied(DomainEvent):
    candidate_id: CandidateId
    job_offer_id: JobOfferId
    application_id: ApplicationId

# calls module
@dataclass
class TranscriptSegment:
    speaker: str  # "emma" | "candidate"
    text: str
    timestamp: float  # seconds from call start; all consumers (storage, analysis) use this convention

@dataclass
class ScreeningCall:
    id: CallId
    application_id: ApplicationId
    status: CallStatus  # e.g. in_progress, completed, failed
    started_at: datetime
    ended_at: datetime | None
    transcript: list[TranscriptSegment]  # stored as ordered list of segments; analysis loads this format

class CallFinished(DomainEvent):
    application_id: ApplicationId
    call_id: CallId

# analysis module
@dataclass
class FitAssessment:
    score: int  # 0-100
    skills: list[str]

@dataclass
class ScreeningAnalysis:
    id: AnalysisId
    application_id: ApplicationId
    fit_score: int
    skills: list[str]
    completed_at: datetime
```

### API contract (base path and routes)

All HTTP and WebSocket APIs use the **base path** `/api`. Chosen routes:

| Method / Type | Path | Purpose |
| --------------|------|---------|
| POST | `/api/applications` | Create application (body: `username`, `job_offer_id`). |
| GET | `/api/applications/{application_id}/analysis` | Get analysis result (fit_score, skills) or 202/404 while pending. |
| WebSocket | `/api/ws/call?application_id={id}` | Call stream; one active call per application_id. |

### APIs / Interfaces

- **POST /api/applications**
  - Request: `{ "username": string, "job_offer_id": string }`
  - Response 201: `{ "application_id": string }`. Duplicate (same username + job_offer_id): idempotent — return 201 with existing `application_id`; no new record.
  - Errors: 400 (validation), 404 (Torre not found), 422 (Torre data invalid), 502/503 (Torre/upstream failure), 503 (broker down — see NFR Reliability).

- **WebSocket /api/ws/call?application_id={application_id}**
  - Query: `application_id` (required). Only one active connection per application_id; new connection for same id is rejected (close with 4xx).
  - **Minimal message schema** (client→server and server→client so Phase 2 backend and Phase 3 frontend can align):
    - **Client → server**: audio chunk (binary PCM or JSON `{ "type": "audio", "payload": "<base64>" }`).
    - **Server → client**: (1) audio chunk — Emma TTS output; (2) control — e.g. `{ "type": "control", "event": "emma_speaking" | "listening" | "call_ended" }` so the UI can show state. Exact payload format (codec, sample rate) TBD in implementation.

- **GET /api/applications/{application_id}/analysis**
  - Response 200: `{ "fit_score": number (0-100), "skills": string[] }`
  - Response 202: Analysis pending (optional).
  - Response 404: Application or analysis not found.

### Algorithms / Logic

- **Fit score**: POC can use (a) embedding similarity between candidate and job offer embeddings, mapped to 0–100, or (b) LLM-based judgment with a short rubric, or (c) rule-based from keyword match. Document chosen approach and fallback when embeddings are missing.
- **Skills extraction**: From transcript + candidate profile; match or infer against job responsibilities/strengths; return list of strings for display.
- **Emma role-only answers**: When candidate intent is "question about role", restrict LLM context to job objective, strengths, responsibilities; no general knowledge. Use system prompt or context window limits to enforce.

---

## Implementation Plan

### Tasks

1. [ ] **Repo and bounded context**
   - [ ] Align repo with bounded context: implement under `src/screening/` with modules `applications/`, `calls/`, `analysis/` (each with domain, application, infrastructure). If the current layout (`src/bounded_context/module/`) is retained, document the mapping from it to the screening modules in this doc or in bounded-context-structure.md.
2. [ ] **Application module**
   - [ ] Domain: `ScreeningApplication`, `Candidate`, `JobOffer`, `JobOfferApplied` event.
   - [ ] Ports: Event publisher interface; Torre client interfaces (bios, opportunities).
   - [ ] ApplicationService: Validate input, call Torre adapters, persist via repositories, publish event; idempotent duplicate (same username + job_offer_id) per API contract.
   - [ ] Infrastructure: HTTP adapters for Torre APIs; RabbitMQ (or in-memory) event publisher.
   - [ ] HTTP: POST /api/applications endpoint; error mapping to 400/404/422/502/503.
3. [ ] **Event subscribers**
   - [ ] GenerateCandidateEmbeddings: Consume JobOfferApplied, fetch candidate text, call embeddings adapter, store.
   - [ ] GenerateJobOfferEmbeddings: Consume JobOfferApplied, fetch job text, call embeddings adapter, store.
   - [ ] GenerateCallPrompt: Consume JobOfferApplied, build prepared questions + role context, store for call.
   - [ ] Embeddings adapter (e.g. OpenRouter or local); retry and dead-letter handling.
4. [ ] **Calls module**
   - [ ] Domain: `ScreeningCall`, `CallStatus`, `TranscriptSegment`, `CallFinished` event; transcript stored as list of segments. TranscriptSegment.timestamp: use offset from call start (e.g. seconds) consistently for storage and analysis.
   - [ ] CallService: Resolve application_id, load prompt, delegate to EmmaService; enforce one active call per application_id (reject new connection with 4xx).
   - [ ] EmmaService: Greeting → wait (e.g. 5s) → Q&A loop (prepared questions); role-only answers; goodbye.
   - [ ] WebSocket handler: `/api/ws/call?application_id=...`; minimal message schema (client audio, server audio, server control); on close publish CallFinished.
   - [ ] LLM adapter (Ollama); STT/TTS adapters (choice for POC).
5. [ ] **Analysis module**
   - [ ] Domain: `ScreeningAnalysis`, `FitAssessment`, subscriber for CallFinished.
   - [ ] AnalysisService: Load transcript (list of TranscriptSegment) and data, compute fit score and skills, persist; document fit-score algorithm and fallback when embeddings are missing.
   - [ ] GET /api/applications/{id}/analysis endpoint; 200/202/404 behavior. Phase 2: do not publish AnalysisCompleted; client polls.
6. [ ] **Integration and config**
   - [ ] Docker Compose or env for Postgres, RabbitMQ, Ollama (if used).
   - [ ] Configuration for Torre base URL, broker URL, LLM/embeddings endpoints.
   - [ ] Document fit-score algorithm and fallback when embeddings are missing (implementation note or ADR).

### Dependencies

- **Requires**: Torre public APIs; database (Postgres); message broker (e.g. RabbitMQ); LLM/voice (e.g. Ollama) and optionally embeddings provider.
- **Blocks**: Phase 3 (frontend will call these APIs and WebSocket).

### Testing Strategy

- **Unit**: ApplicationService (with mocked Torre and event publisher); EmmaService (with mocked LLM/STT/TTS); AnalysisService (fit score and skills logic with canned transcript).
- **Integration**: POST /api/applications against real Torre (or contract tests with mocked Torre); event publish and subscribe (e.g. in-process or test broker); WebSocket handshake and message flow with stub client.
- **E2E**: Optional: create application → open WebSocket → complete minimal Q&A → close → poll analysis until 200; verify fit_score and skills. Can be automated in Phase 3.

---

## Non-Functional Requirements

### Performance

- Application creation: Target p95 &lt; 3s including Torre calls and persist.
- WebSocket: Low latency for Emma replies (streaming; target first byte &lt; 2s for POC).
- Analysis: Complete within 30s of CallFinished for typical transcript length.

### Security

- POC: No auth required for application and analysis endpoints; document that production would add auth and scope by user/tenant.
- WebSocket: Validate application_id and ensure one active call per application; reject invalid or duplicate connections.

### Reliability

- Torre timeout and retry: Configurable timeout (e.g. 5s), one retry; then fail request.
- Event delivery: At-least-once when the broker is up; idempotent handlers where possible (e.g. analysis upsert by application_id). When the broker is down, the application request fails (publish is synchronous before responding); the server returns 503 and does not persist the application — no best-effort fire-and-forget.
- Analysis failure: Retry with backoff; after max retries persist "failed" state so UI can show message.

---

## Design Decisions

### Decision 1: Event name CallFinished vs UserLeftCall

- **Context**: Bounded context doc mentions UserLeftCall → analysis; PRD says CallFinished when WebSocket closes.
- **Chosen**: Use `CallFinished` in this design to match PRD; emitted when the server closes the call (normal end or client disconnect). Analysis subscriber reacts to CallFinished.
- **Rationale**: Single event for "call ended" keeps contract simple; implementation can map to internal naming if needed.

### Decision 2: Data preparation in applications module

- **Context**: Bounded context suggests Option B — keep data prep (embeddings, call prompt) in applications module as subscribers to JobOfferApplied.
- **Chosen**: Implement GenerateCandidateEmbeddings, GenerateJobOfferEmbeddings, and GenerateCallPrompt as event subscribers; they can live under applications or a shared screening entrypoint.
- **Rationale**: Keeps applications as the trigger; avoids a separate data_preparation module for POC.

### Decision 3: Emma role-only answers via context restriction

- **Context**: PRD requires Emma to answer candidate questions about the role using only job/role data.
- **Chosen**: Pass only job objective, strengths, and responsibilities into the LLM context for "role Q&A" turns; system prompt instructs Emma not to use external knowledge.
- **Rationale**: Reduces hallucination and keeps answers consistent with the job posting.

### Decision 4: Duplicate application — idempotent return

- **Context**: Same username + job_offer_id may be submitted more than once; API contract must be unambiguous.
- **Chosen**: Idempotent behaviour: if an application already exists for the same username and job_offer_id, return 201 with the existing `application_id`; do not create a new record or publish a new event.
- **Rationale**: Simplifies client retries and avoids duplicate events/subscribers for the same logical application.

### Decision 5: One active call per application_id

- **Context**: Multiple tabs or retries could open more than one WebSocket for the same application_id; policy must be testable.
- **Chosen**: Only one active call per application_id. A new WebSocket connection for an application_id that already has an active call is rejected: server closes the new connection with code **4409** and does not replace the existing call.
- **Rationale**: Prevents overlapping Emma sessions and ensures a single transcript per application for analysis.

---

## Open Questions

- [ ] Exact Torre API paths: Confirm `api/suite/opportunities` vs `api/opportunities` (or other) for job offer.
- [ ] WebSocket payload format: Codec, sample rate, and exact JSON shape for audio and control messages — align with frontend in Phase 3; minimal roles (client audio, server audio, server control) are defined in API contract above.
- [ ] Fit score formula: Final choice of embedding similarity vs LLM rubric vs rules; and behavior when embeddings are missing.

---

## Risks & Mitigations

- **Torre API rate limits or downtime**: Mitigation: Respect Retry-After if present; cache job offer (and optionally bios) briefly by id to reduce duplicate calls; document limits for operators.
- **LLM/voice latency**: Mitigation: Use streaming TTS and smaller chunks; set timeout for "no answer" to avoid long waits; POC accepts higher latency and documents for Phase 3 tuning.

---

## Success Metrics

- Application creation and call flow are testable via API and WebSocket without the frontend.
- Analysis is produced and stored after call end; GET analysis returns fit_score and skills.
- Emma answers candidate role questions using only job/role data (verified by manual or automated test).
- All Phase 2 user stories (US2.1–US2.4) acceptance criteria are met.

---

## References

- PRD: [docs/prd-screening-simulation.md](../prd-screening-simulation.md) — Phase 2
- Bounded context: [docs/bounded-context-structure.md](../bounded-context-structure.md)
- Phase 1 design: [docs/design-specs/design-screening-frontend-phase1.md](design-screening-frontend-phase1.md)
- Torre APIs: `GET https://torre.ai/api/genome/bios/<username>`, `GET https://torre.ai/api/suite/opportunities/<job_offer_id>` (confirm paths in implementation)
