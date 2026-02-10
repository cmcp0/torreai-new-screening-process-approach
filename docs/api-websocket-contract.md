# API and WebSocket Contract (Screening POC)

This document describes the HTTP and WebSocket contracts between the frontend and the screening backend for Phase 3 integration. The backend is unauthenticated for this POC.

---

## HTTP — Create application

- **Endpoint**: `POST /api/applications`
- **Request body**: `{ "username": string, "job_offer_id": string }` (non-empty)
- **Response 201**: `{ "application_id": string }`
- **Response 400**: `{ "detail": string }` — validation (e.g. missing params)
- **Response 404**: `{ "detail": string }` — Torre user/job not found
- **Response 422**: `{ "detail": string | array }` — invalid data from upstream
- **Response 502/503**: `{ "detail": string }` — upstream error or unavailable
- **CORS**: Backend allows frontend origin (e.g. `Origin: http://localhost:5173`). Configure via `SCREENING_CORS_ORIGINS` (comma-separated).

---

## HTTP — Get analysis

- **Endpoint**: `GET /api/applications/{application_id}/analysis`
- **Response 200**: `{ "fit_score": number, "skills": string[], "failed"?: boolean }` — analysis ready. `fit_score` is 0–100. If `failed` is true, analysis could not be completed (e.g. after retries); client may show "Analysis failed".
- **Response 202**: Analysis pending. Body may include `{ "detail": "Analysis pending" }`. Client should poll again after a short interval.
- **Response 404**: Application or analysis not found.

---

## WebSocket — Call

- **Endpoint**: `WS /api/ws/call?application_id=<uuid>`
- **URL**: Derive from API base (e.g. `http://localhost:8000` → `ws://localhost:8000/api/ws/call?application_id=...`).

### Close codes

- **4000**: Invalid `application_id`
- **4409**: Call already active for this application
- **1000**: Normal closure (call ended)

### Messages from server (JSON)

- **Control**: `{ "type": "control", "event": "listening" | "emma_speaking" | "call_ended" }`
  - `listening`: Emma finished speaking; backend is waiting for candidate input.
  - `emma_speaking`: Emma is speaking (e.g. greeting, question, answer).
  - `call_ended`: Call finished; client should show post-call UI and may close the socket.
- **Text**: `{ "type": "text", "text": string }` — Emma utterance or transcript segment. Client should append to transcript display.
- **Audio chunk (optional)**: `{ "type": "audio_chunk", "speaker": "emma", "codec": string, "seq": number, "data_b64": string, "is_final": boolean }`
  - Backward compatible: server may send text-only, audio-only, or both.
  - When audio chunks are present, `is_final=true` marks Emma audio completion for that turn.

### Messages from client

- **Plain text**: Treated as the candidate’s reply.
- **JSON**: `{ "type": "text", "text": string }` — preferred. Backend accepts either; use JSON for consistency.
- **Audio start**: `{ "type": "audio_start", "codec": "pcm16" | "webm-opus", "sample_rate_hz": number }`
- **Audio chunk**: `{ "type": "audio_chunk", "data_b64": string, "seq": number, "is_final": boolean }`
- **Audio end**: `{ "type": "audio_end" }`
- Text mode remains supported indefinitely as a compatibility fallback.

---

## Frontend data types (TypeScript)

```ts
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
  failed?: boolean
}
```

---

## Error handling (frontend)

- **4xx/5xx**: Prefer displaying `response.detail` when present (if `detail` is a string, use it; if a list, use the first element or join). Otherwise use a generic message per status (e.g. 404 → "Not found", 5xx → "Service unavailable").
- **Network failure or timeout**: Show a generic message (e.g. "Service unavailable" or "Failed to create application") and offer a recovery action (e.g. "Try again", "Go to application").

---

## Domain events (backend)

The backend publishes domain events (e.g. when using RabbitMQ). **AnalysisCompleted** is emitted when analysis for an application finishes successfully (after a screening call). It carries `application_id` and `analysis_id`. There is no change to the current polling contract; future consumers of this event may use it for push notifications, SSE, or downstream workflows.
