# Design Document: Screening Integration — Phase 3

## Metadata

- **Related PRD**: [PRD: Screening Simulation (POC)](../prd-screening-simulation.md)
- **Phase**: Phase 3 — Integration
- **Status**: Draft
- **Last Updated**: 2025-02-02
- **Author**: TBD
- **Reviewers**: TBD

---

## Overview

This design doc specifies how to connect the Phase 1 frontend and Phase 2 backend so that a candidate can complete the full screening flow end-to-end without manual steps: application creation → consent → call (WebSocket + Emma) → analysis page with fit score and skills. It covers frontend API/WebSocket integration, error handling and loading states, API/WebSocket contract documentation, and Docker Compose (or equivalent) to run the full stack locally for E2E and development.

---

## Context

- **Problem**: Phase 1 delivers UI with mock data; Phase 2 delivers backend APIs and WebSocket. The two are not connected. A candidate cannot complete the real flow from a single entry point.
- **Goals**: (1) Frontend calls backend to create application and redirects to call page. (2) WebSocket connection and audio/control streaming between frontend and backend during the call. (3) Consent and call flow wired to backend (start call only after consent). (4) After call end, redirect to analysis page; frontend fetches or polls until analysis is ready and displays fit score and skills. (5) Single-command local run of full stack (frontend, backend, Postgres, RabbitMQ, Ollama) for E2E and development.
- **Scope**: In scope — integrated E2E flow; frontend API client and WebSocket client; error handling and loading states; API/WebSocket contract documentation; Docker Compose (or equivalent). Out of scope — production deployment; auth; video; changes to Phase 1/2 business logic beyond wiring.

- **Query param naming**: The call page uses `application` (`/call?application=<id>`); the analysis page uses `application_id` (`/analysis?application_id=<id>`). Implementers must handle both. This design preserves the existing Phase 1 route contracts; standardizing on a single name (e.g. `application_id` everywhere) may be done in a later refactor and would require updating call route and PostCallModal navigation.

---

## Functional Specifications

### Feature 1: Application Creation Integration

**Description**: The application page calls the backend `POST /api/applications` with `username` and `job_offer_id` from query params. On success, the frontend redirects to `/call?application=<application_id>`. On error, the frontend shows a concrete message: `response.detail` when present (string or first element if list), otherwise a generic message per status (see FR-1.4).

**User story**: US3.1 — As a candidate, I want the frontend to use the application id and call/analysis APIs so that I can complete the full flow without manual steps.

**Acceptance criteria** (from PRD):

- Given I have submitted an application successfully, when the backend returns an application id, then I am redirected to `/call?application=<id>`.

**Functional requirements**:

- FR-1.1: The frontend SHALL call `POST /api/applications` with body `{ "username": string, "job_offer_id": string }` using values from route query params.
- FR-1.2: The frontend SHALL use a configurable base URL for the backend API (e.g. environment variable or Vite `import.meta.env`).
- FR-1.3: On HTTP 201, the frontend SHALL read `application_id` from the response and redirect to `/call?application=<application_id>`.
- FR-1.4: On HTTP 400, 404, 422, 502, 503, the frontend SHALL display an error message and SHALL NOT redirect. Display `response.detail` when present (if `detail` is a string, use it; if a list, use the first element or join). Otherwise use a generic message per status (e.g. 404 → "Not found", 5xx → "Service unavailable").
- FR-1.5: On network failure or timeout, the frontend SHALL display a generic error (e.g. "Failed to create application" or "Service unavailable") and offer a way to try again.

**User flows**:

1. User opens `/application?username=johndoe&job_offer_id=abc123`.
2. Frontend shows loading state and sends `POST /api/applications` to backend.
3. Backend returns 201 with `{ "application_id": "uuid" }` → frontend redirects to `/call?application=uuid`.
4. Alternative: Backend returns 404 (e.g. Torre user/job not found) → frontend shows "not found" or equivalent; user can correct URL or try again.
5. Alternative: Backend returns 503 → frontend shows "Service unavailable" or equivalent.

**Edge cases**:

- Missing or empty `username` / `job_offer_id` in URL: Frontend validates before calling API; show "Username and job offer are required" (already in Phase 1).
- CORS: Backend SHALL allow frontend origin (e.g. `http://localhost:5173` in dev); document in API contract.
- Response body on 4xx/5xx: Display `detail` when present (string as-is; list → first element or join). Otherwise generic per status (404 vs 5xx). See FR-1.4.

---

### Feature 2: WebSocket Call Connection and Control

**Description**: The call page, after consent is accepted, establishes a WebSocket connection to the backend at `/api/ws/call?application_id=<id>`. The frontend sends and receives control and text messages according to the backend contract; connection state (connecting, connected, ended) is driven by the real WebSocket lifecycle. When the backend closes the WebSocket (call finished), the frontend shows the post-call modal and allows navigation to the analysis page.

**User story**: US3.1 (call leg) — Frontend uses application id and call APIs so the candidate can complete the full flow.

**Acceptance criteria** (from PRD):

- Consent and call flow wired to backend (start call only after consent).
- WebSocket connection and audio streaming between frontend and backend during the call.

**Functional requirements**:

- FR-2.1: The frontend SHALL connect to the WebSocket only after the user has accepted the consent form.
- FR-2.2: The frontend SHALL connect to `ws://<backend_host>/api/ws/call?application_id=<application_id>` (or `wss://` in production); backend host SHALL be configurable (same base as API or dedicated WebSocket URL).
- FR-2.3: The frontend SHALL send and receive messages in the format defined by the backend (see API/WebSocket contract section).
  - Compatibility rule: frontend SHOULD support both text turns (`{type:\"text\"}`) and audio turn messages (`audio_start`/`audio_chunk`/`audio_end`) so calls continue even when one path is unavailable.
- FR-2.4: The frontend SHALL update call UI state (e.g. connecting → connected) based on WebSocket open/close and control messages (e.g. `emma_speaking`, `listening`, `call_ended`).
- FR-2.5: When the WebSocket closes normally (call ended by backend), the frontend SHALL show the post-call modal with the option to go to the analysis page.
- FR-2.6: When the WebSocket closes with an error (e.g. invalid application_id, call already active), the frontend SHALL show an error state and optionally allow the user to return to the application page.

**User flows**:

1. User is on `/call?application=<id>`, accepts consent.
2. Frontend opens WebSocket to `/api/ws/call?application_id=<id>`.
3. Backend accepts connection; sends control/text (e.g. greeting). Frontend shows "In call" and transcript/controls as per Phase 1 design.
4. Candidate and Emma interact; frontend displays transcript and state from messages.
5. Backend sends goodbye and closes WebSocket → frontend sets state to "ended", shows post-call modal.
6. User clicks "View analysis" → navigate to `/analysis?application_id=<id>`.

**Edge cases**:

- Invalid or missing `application_id` in URL: Already handled in Phase 1 (missing application message). If WebSocket returns 4000 or similar, show "Invalid application" and link back to application.
- Call already active for this application (backend close code 4409): Show "A call is already in progress for this application" and option to go back.
- WebSocket connection failure (network, backend down): Show "Could not connect to call" and option to try again or go back.
- User navigates away during call: WebSocket closes; if user returns to call page, they can restart from application (one call per application per backend design).

---

### Feature 3: Analysis Page Integration (Polling/Fetch)

**Description**: The analysis page uses the backend `GET /api/applications/{application_id}/analysis` to fetch results. When analysis is not yet ready, the backend returns 202 (Analysis pending); the frontend polls at a defined interval until the backend returns 200 with fit score and skills, then displays them. On 404, the frontend shows "Application not found" or equivalent.

**User story**: US3.1 (analysis leg) — Given the call has ended, when I go to the analysis page, then the frontend fetches or polls until analysis is ready and displays the fit score and skills.

**Acceptance criteria** (from PRD):

- Given the call has ended, when I go to the analysis page, then the frontend fetches or polls until analysis is ready and displays the fit score and skills.

**Functional requirements**:

- FR-3.1: The frontend SHALL call `GET /api/applications/{application_id}/analysis` using `application_id` from route query param.
- FR-3.2: On HTTP 200, the frontend SHALL display the returned `fit_score` and `skills` (same UI as Phase 1).
- FR-3.3: On HTTP 202 (Analysis pending), the frontend SHALL show a loading/waiting state and SHALL poll the same endpoint again after a configurable interval (e.g. 2–3 seconds); SHALL cap retries or duration to avoid infinite polling (e.g. max 5 minutes or 100 attempts).
- FR-3.4: On HTTP 404, the frontend SHALL show "Application not found" (or equivalent) and a link back to the application page.
- FR-3.5: On HTTP 5xx or network error, the frontend SHALL show an error message and optionally allow retry.

**User flows**:

1. User lands on `/analysis?application_id=<id>` (e.g. from post-call modal).
2. Frontend sends `GET /api/applications/<id>/analysis`.
3. If 202: show "Analyzing your call…", repeat request after 2–3 s.
4. If 200: show fit score and skills.
5. If 404: show "Application not found", link to application.
6. If 5xx: show error, optional retry.

**Edge cases**:

- Missing `application_id` in URL: Already handled in Phase 1 (param error). Same behavior.
- Analysis takes longer than poll cap: Show "Analysis is taking longer than expected. Please check back later." and optional "Retry" or link to application.
- User refreshes analysis page: Polling starts again; backend returns 200 when ready (idempotent).

---

### Feature 4: Error Handling and Loading States

**Description**: All integration points (application create, WebSocket call, analysis fetch) have consistent error handling and loading states so the candidate sees clear feedback and recovery options.

**Functional requirements**:

- FR-4.1: The frontend SHALL show a loading state whenever a request or WebSocket connection is in progress (application create, connecting to call, fetching analysis).
- FR-4.2: The frontend SHALL show error messages per the same rule as FR-1.4: display `response.detail` when present (string or first element if list); otherwise a generic message per status (e.g. 404 → "Not found", 5xx → "Service unavailable"). For network errors or timeouts, use a generic fallback (e.g. "Service unavailable").
- FR-4.3: The frontend SHALL provide at least one recovery action per error state (e.g. "Try again", "Go to application", "Back to application").

**Edge cases**:

- Slow backend: Loading states remain until response or timeout; consider timeout values (e.g. 30 s for application create, 10 s for analysis fetch) and show timeout error if exceeded.

---

### Feature 5: Docker Compose (or Equivalent) for Full Stack

**Description**: A single command (e.g. `docker compose up`) starts the full stack locally: frontend dev server (or built static), backend (FastAPI), Postgres, RabbitMQ, and Ollama (or configured LLM/voice services). This enables E2E testing and development without manually starting each service.

**Functional requirements**:

- FR-5.1: The project SHALL provide a Docker Compose file (or equivalent) that defines services: backend, frontend, Postgres, RabbitMQ, Ollama (or stubs if optional for minimal E2E). For local E2E and development, the **default setup uses the Vite dev server** for the frontend (hot reload, single defined setup); an optional profile may serve built static files via nginx for production-like E2E if needed.
- FR-5.2: Backend SHALL read connection settings (DB, RabbitMQ) from environment variables that Compose can set.
- FR-5.3: Frontend SHALL read backend API base URL from environment (or build-time variable) so that when run under Compose, it points to the backend service.
- FR-5.4: Documentation SHALL describe how to run the full stack (e.g. `docker compose up`) and any required env files or secrets. E2E tests SHALL assume the full stack is running via `docker compose up` (or `docker compose --profile e2e up` if a dedicated E2E profile is added).

**User flows**:

1. Developer runs `docker compose up` (or `docker compose up -d`).
2. Frontend is available at e.g. `http://localhost:5173` (or 80); backend at e.g. `http://localhost:8000`.
3. Developer opens frontend URL with `?username=...&job_offer_id=...` and can run through the full flow.

**Edge cases**:

- Ollama/LLM not required for smoke E2E: Consider a "minimal" profile that runs backend + frontend + DB + RabbitMQ only, with mock or skip for Emma if acceptable; document.
- Port conflicts: Document default ports and how to override via env.

---

## Technical Design

### Architecture

- **Frontend** (Vue.js, Vite): SPA that talks to backend over HTTP (application create, analysis GET) and WebSocket (call). Backend base URL and WebSocket URL are configurable (env/build).
- **Backend** (FastAPI): Existing Phase 2 app; no change to route contracts. CORS must allow frontend origin.
- **Integration points**:
  1. `POST /api/applications` ← ApplicationPage
  2. `GET /api/applications/{id}/analysis` ← AnalysisPage (poll until 200)
  3. `WebSocket /api/ws/call?application_id=` ← CallPage (after consent)

```text
+------------------+     HTTP POST /api/applications      +------------------+
|  ApplicationPage | ---------------------------------->  |  Backend         |
|  (redirect on 201)| <----------------------------------  |  /api/applications|
+------------------+     { application_id }                +------------------+
         |
         | redirect /call?application=<id>
         v
+------------------+     WebSocket /api/ws/call?application_id=  +------------------+
|  CallPage        | <=========================================>  |  Backend         |
|  (after consent) |     control + text messages                  |  ws handler      |
+------------------+                                              +------------------+
         |
         | post-call modal -> /analysis?application_id=
         v
+------------------+     HTTP GET /api/applications/{id}/analysis  +------------------+
|  AnalysisPage    | ---------------------------------------------->  |  Backend         |
|  (poll until 200)| <----------------------------------------------  |  analysis route  |
+------------------+     200 { fit_score, skills } or 202          +------------------+
```

### Components

- **Frontend API client**: Replace or extend `apps/frontend/src/api/mock.ts` with a real client that calls backend base URL (e.g. `fetch` or axios). Export `createApplication`, `getAnalysis` with same TypeScript interfaces; add optional WebSocket helper or keep WebSocket logic in CallPage/composable.
- **Frontend env/config**: Use Vite `import.meta.env.VITE_API_BASE_URL` (or similar) for HTTP and WebSocket base; default in dev to `http://localhost:8000`.
- **Call page WebSocket**: In CallPage (or a composable), after consent: open WebSocket, send/receive messages per backend contract, update local state (transcript, status), handle close (normal → post-call modal; error → error state).
- **Analysis page polling**: In AnalysisPage, on mount with valid `application_id`: call GET analysis; if 202, set timer and call again; if 200, set result and stop; if 404/5xx, set error. Cap polling (max time or count).
- **Backend CORS**: Add CORS middleware in FastAPI app allowing frontend origin (e.g. `http://localhost:5173` in dev, configurable).
- **Docker Compose**: New file `docker-compose.yml` (or `compose.yaml`) at repo root with services: `backend`, `frontend` (Vite dev server by default; optional profile for nginx + static), `postgres`, `rabbitmq`, `ollama` (or optional). `.env.example` for backend DB and broker URLs.

### Data Models (Frontend)

Existing types in `apps/frontend/src/types/index.ts` remain; align with backend response shapes:

```typescript
// Already defined; backend returns same shape
interface ApplicationParams {
  username: string
  job_offer_id: string
}

interface ApplicationResult {
  application_id: string
}

interface AnalysisResult {
  fit_score: number  // 0–100
  skills: string[]
}
```

Backend analysis response: `fit_score: int` (0–100), `skills: list`. Frontend uses as-is.

### APIs/Interfaces (Contract Documentation)

**HTTP — Create application**

- **Endpoint**: `POST /api/applications`
- **Request body**: `{ "username": string, "job_offer_id": string }` (non-empty)
- **Response 201**: `{ "application_id": string }`
- **Response 400**: `{ "detail": string }` — validation (e.g. missing params)
- **Response 404**: `{ "detail": string }` — Torre user/job not found
- **Response 422**: `{ "detail": string | array }` — invalid data from upstream
- **Response 502/503**: `{ "detail": string }` — upstream error or unavailable
- **CORS**: Allow frontend origin (e.g. `Origin: http://localhost:5173`).

**HTTP — Get analysis**

- **Endpoint**: `GET /api/applications/{application_id}/analysis`
- **Response 200**: `{ "fit_score": number, "skills": string[] }` — analysis ready
- **Response 202**: Analysis pending (body may include `detail`: "Analysis pending")
- **Response 404**: Application or analysis not found

**WebSocket — Call**

- **Endpoint**: `WS /api/ws/call?application_id=<uuid>`
- **Close codes**: 4000 — invalid application_id; 4409 — call already active for this application.
- **Messages from server** (JSON):
  - Control: `{ "type": "control", "event": "listening" | "emma_speaking" | "call_ended" }`
  - Text: `{ "type": "text", "text": string }` (Emma utterance or transcript segment)
- **Messages from client**: Plain text (candidate response) or JSON `{ "type": "text", "text": string }`. Backend `_extract_candidate_text` accepts either; prefers JSON with `type: "text"` and `text` field.

Document the above in a single file: e.g. `docs/api-websocket-contract.md` (deliverable).

### Algorithms/Logic

- **Analysis polling**: Interval 2–3 s; max duration 5 min (or 100 requests). On 200: stop and render. On 202: schedule next. On 404/5xx: stop and show error.
- **WebSocket URL**: Derive from API base URL (replace `http` with `ws`, same host/port) or separate `VITE_WS_URL` if needed (e.g. different host in production).

---

## Implementation Plan

### Tasks

1. [x] **Backend CORS**: Add CORS middleware to FastAPI app (allow frontend origin from env or default localhost:5173).
2. [x] **Frontend env**: Add `VITE_API_BASE_URL` (and optional `VITE_WS_URL`) in `.env.example` and use in API client; default `http://localhost:8000` for dev.
3. [x] **API client**: Replace mock in `apps/frontend/src/api/mock.ts` (or new `api/client.ts`) with real HTTP calls to `POST /api/applications` and `GET /api/applications/{id}/analysis`; keep same function signatures and types.
4. [x] **ApplicationPage**: Switch from mock to real API client (already structured for redirect on success and error on failure).
5. [x] **CallPage**: After consent, open WebSocket to backend; implement message handling (control + text), update transcript and status; on close, show post-call modal or error. Remove mock timeout/setTimeout that simulates connection and transcript.
6. [x] **CallUI**: If needed, accept transcript and status from parent (CallPage) that are driven by WebSocket; keep "End call" if backend supports client-initiated end (or hide and rely on backend close).
7. [x] **AnalysisPage**: Replace single mock fetch with polling: GET analysis, on 202 poll again with backoff/cap, on 200 set result, on 404/5xx set error.
8. [x] **API/WebSocket contract doc**: Create `docs/api-websocket-contract.md` with HTTP and WebSocket contracts as above.
9. [x] **Docker Compose**: Add `docker-compose.yml` with services backend, frontend (Vite dev server by default; optional profile for nginx + static), postgres, rabbitmq, ollama (or optional); backend env for DB and broker; frontend build-time env for API URL.
10. [x] **README or docs**: Document how to run full stack (`docker compose up`), required env, and optional minimal profile. State that E2E tests assume the stack is running via `docker compose up` (or `docker compose --profile e2e up` if an E2E profile exists).

**Note**: The optional profile for nginx serving built static frontend (production-like E2E) is not implemented; the default setup is Vite dev server only. Add an `e2e-static` (or similar) profile if production-like E2E is required.

### Dependencies

- **Requires**: Phase 1 (frontend pages and UI) and Phase 2 (backend APIs and WebSocket) completed.
- **Blocks**: E2E tests against real stack; production deployment (separate concern).

### Testing Strategy

- **Unit tests**: Frontend API client (mocked fetch/WebSocket) for success and error paths; analysis polling logic (max retries, 200/202/404).
- **Integration tests**: Backend already has integration tests for applications and analysis; add or extend for CORS if needed.
- **E2E tests**: With full stack running (Docker Compose or dev servers), run E2E (e.g. Playwright/Cypress): open application URL → submit → consent → connect WebSocket (optional: stub Emma for speed) → end call → analysis page shows result. Optional: E2E with real Emma and polling until analysis ready.

---

## Non-Functional Requirements

### Performance

- **Application create**: Frontend timeout e.g. 30 s; backend Torre calls already have timeout (Phase 2).
- **Analysis polling**: Interval 2–3 s; avoid aggressive polling (e.g. not below 1 s).
- **WebSocket**: No additional latency beyond backend; frontend updates UI on each message.

### Security

- **CORS**: Restrict to frontend origin(s); avoid `*` in production.
- **POC**: No auth; document that API/WebSocket are unauthenticated for POC.

### Reliability

- **Error handling**: All integration points return or show errors; no silent failures.
- **Polling cap**: Prevent infinite loop on analysis (max time or count).

---

## Design Decisions

### Decision 1: Polling vs WebSocket for analysis ready

**Context**: Analysis runs asynchronously after call end; frontend needs to know when it’s ready.

**Options considered**: (A) Poll GET analysis until 200. (B) WebSocket or SSE from backend when analysis ready. (C) Long polling.

**Chosen**: Polling GET analysis (A).

**Rationale**: Backend already exposes GET with 202/200; no new endpoint or channel. Simple and stateless.

**Trade-offs**: Slight delay (poll interval) before user sees result; acceptable for POC.

---

### Decision 2: Single API base URL for HTTP and WebSocket

**Context**: Frontend needs backend host for REST and WebSocket.

**Options considered**: (A) One base URL (e.g. `http://localhost:8000`); derive WebSocket URL by replacing `http` with `ws`. (B) Separate env vars for API and WebSocket.

**Chosen**: Single base URL; derive WebSocket URL in code (A) unless deployment requires different hosts.

**Rationale**: Simpler config for local and most deployments.

**Trade-offs**: If production uses different host/port for WebSocket, add `VITE_WS_URL` later.

---

### Decision 3: Docker Compose for full stack

**Context**: PRD asks for single-command run of full stack.

**Options considered**: (A) Docker Compose. (B) Script that starts processes locally. (C) Document only.

**Chosen**: Docker Compose (A).

**Rationale**: Reproducible; matches common practice; same file can be used for E2E.

**Trade-offs**: Requires Docker; optional "minimal" profile if Ollama is heavy for some devs.

---

## POC: text-based call UI (PRD is audio-only)

The **PRD specifies an audio-only** screening call: the candidate should hear Emma and respond by voice. The **current POC implementation uses text** over the WebSocket (no STT/TTS): the backend sends Emma’s lines as text messages and the frontend shows a “Your reply” text input so the candidate can type answers. This was done so the full flow (application → call → analysis) works end-to-end without an audio pipeline. When audio (STT/TTS) and streaming are added, the contract and frontend should switch to audio-only; the transcript can remain for accessibility. Until then, the text input is the supported way to respond.

## Open Questions

- [ ] WebSocket client message format is documented: backend accepts plain text or `{ "type": "text", "text": string }`; frontend can use either.
- [ ] Audio streaming: Phase 2 backend may send text-only (transcript); if audio (STT/TTS) is added later, contract and frontend handling will need an update.
- [ ] Ollama in Docker: Whether to include Ollama in default Compose profile or optional; image size and startup time vs E2E fidelity.

---

## Risks & Mitigations

- **Risk 1**: Backend and frontend base URL misconfiguration in Docker (frontend can’t reach backend).  
  **Mitigation**: Document env vars; use service names in Compose (e.g. `http://backend:8000` for server-side render or build-time inject for SPA).
- **Risk 2**: CORS blocking requests in dev.  
  **Mitigation**: Add CORS middleware in Phase 3 first task; allow frontend origin from env.
- **Risk 3**: Analysis polling too aggressive or infinite.  
  **Mitigation**: Cap by time (5 min) or count (100); show "taking longer" message after cap.

---

## Success Metrics

- A candidate can complete application → consent → call → see analysis page with fit score and skills (E2E flow works).
- Invalid username or job_offer_id show concrete messages (e.g. backend `detail` or "Not found"; no crash, clear error).
- Full stack can be started with a single command (e.g. `docker compose up`).
- API/WebSocket contract is documented for frontend and backend consumers.

---

## References

- PRD: [docs/prd-screening-simulation.md](../prd-screening-simulation.md) — Phase 3
- Related design docs: [design-screening-frontend-phase1.md](design-screening-frontend-phase1.md), [design-screening-backend-phase2.md](design-screening-backend-phase2.md)
- Bounded context: [docs/bounded-context-structure.md](../bounded-context-structure.md)
- Backend routes: `apps/backend/routes/` (applications, analysis, ws)
- Frontend views: `apps/frontend/src/views/` (ApplicationPage, CallPage, AnalysisPage)
