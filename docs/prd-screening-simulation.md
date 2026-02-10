# Product Requirements Document: Screening Simulation (POC)

## Overview

- **Product Name**: Screening Simulation (POC)
- **Version**: 0.1
- **Status**: Draft
- **Last Updated**: 2025-02-01
- **Owner**: TBD

This product is an audio-only screening simulation where a candidate applies to a job offer, completes a screening call with Emma (Torre.ai’s AI agent), and receives a post-call analysis with a fit score.

**POC implementation note:** The current build uses browser STT/TTS when available, and falls back to a text reply input when voice capture is unavailable or denied. The product goal remains audio-only; the text fallback keeps the flow operable without a full audio pipeline. It uses Torre.ai public APIs for candidate and job data, persists applications, and follows an event-driven flow from application → call → analysis. The implementation aligns with the bounded context structure described in [bounded-context-structure.md](bounded-context-structure.md) (applications, calls, analysis modules).

---

## Problem Statement

Candidates need a low-friction way to complete initial screening for a job without scheduling a live interview. Recruiters and job posters need consistent, scalable screening and a clear signal of candidate fit (e.g. a score) to prioritize follow-ups. Manual screening does not scale and introduces inconsistency. This POC demonstrates an AI-powered, audio-only screening flow that simulates an interview with Emma and produces a fit assessment for the Software Development Contributor role at Torre.ai.

---

## Goals & Objectives

- **Primary goal**: Simulate end-to-end screening: candidate enters via application URL → backend fetches and persists candidate and job data → candidate completes an audio-only call with Emma (prepared questions, candidate can ask about the role) → after the call, analysis runs and the candidate can view fit score and skills.
- **Success metrics**: A candidate can complete the full flow (application → consent → call → analysis page) and see a fit score; backend correctly fetches Torre APIs, persists data, emits events, and runs analysis on call end.
- **Target users**: Candidate (primary); recruiter/job poster (indirect, via analysis results).

---

## Product Phases

### Phase 1: Frontend — Design System, Pages, Call Flow

**Goal**: Deliver the UI for application entry, consent, call experience, and analysis so that the user journey is defined and implementable without backend dependency for static/UX flow.

**Scope**:
- Design system (Material Design, Tailwind, Vue.js).
- Application page at `/application?username=...&job_offer_id=...` (read query params, show loading/error/not-found states).
- On successful application creation, redirect to `/call?application=<application_id>`.
- Call page: consent form (user must accept to continue); call UI (audio-only, connection state); post-call modal (“call ended”) with button to go to analysis.
- Analysis page at `/analysis?application_id=...` with loading/waiting state and display of fit score and skills when ready.

**Deliverables**: Design system; application page; call page (consent + call UI); analysis page.

**Dependencies**: None (frontend can be built with mock data/states).

**Success Criteria**: All routes and UI states are implementable from this spec; design system is consistent; consent blocks call start until accepted.

---

### Phase 2: Backend — Services, Call Flow

**Goal**: Implement APIs, persistence, Torre integration, event publishing, Emma call flow (WebSocket), and post-call analysis so that the full screening flow can be executed and tested via API/WebSocket.

**Scope**:
- **Application**: Endpoint that accepts `username` and `job_offer_id`; calls Torre APIs (`/api/genome/bios/<username>`, `/api/suite/opportunities/<job_offer_id>`); extracts from user (full name, skills/strengths, jobs) and from job offer (objective, strengths, responsibilities); persists candidate and job offer; publishes `JobOfferApplied` (with DB `candidate_id` and `job_offer_id`); returns `application_id`. On error, returns error so frontend can show “not found.”
- **Event subscribers** (on `JobOfferApplied`): GenerateCandidateEmbeddings; GenerateJobOfferEmbeddings; GenerateCallPrompt (call template with prepared questions).
- **Call**: WebSocket for streaming; Emma greeting → wait for candidate response (e.g. 5s) → Q&A loop (Emma asks prepared questions; candidate may ask questions about the role; Emma answers from role/job data only); Emma says goodbye and closes call; WebSocket closes; publish `CallFinished`.
- **Analysis**: On `CallFinished`, run analysis (fit score, skills); persist result for the analysis page.

**Deliverables**: Application service and Torre adapters; event publishing; embedding and call-prompt subscribers; call/Emma service and WebSocket handler; analysis service and persistence.

**Dependencies**: Torre public APIs; database; message broker for events (e.g. RabbitMQ); LLM/voice for Emma (e.g. Ollama).

**Success Criteria**: Application creation and call flow are testable via API/WebSocket; analysis is produced and stored after call end; Emma answers only about the role.

---

### Phase 3: Integration

**Goal**: Connect frontend and backend so that a candidate can complete the full flow end-to-end without manual steps.

**Scope**:
- Frontend calls backend to create application; on success, redirect to `/call?application=<id>`.
- WebSocket connection and audio streaming between frontend and backend during the call.
- Consent and call flow wired to backend (start call only after consent).
- After call end, redirect to analysis page; frontend polls or fetches until analysis is ready; display fit score and skills.
- Docker Compose (or equivalent) to run the full stack locally (frontend, backend, Postgres, RabbitMQ, Ollama) for E2E and development.

**Deliverables**: Integrated E2E flow; error handling and loading states; documentation of API/WebSocket contracts; Docker Compose (or equivalent) for local run of full stack.

**Dependencies**: Phase 1 and Phase 2 completed.

**Success Criteria**: A candidate can complete application → consent → call → see analysis page with fit score and skills; errors (e.g. invalid username/job_offer_id) show appropriate messages; full stack can be started with a single command (e.g. `docker compose up`).

---

## High-Level Flow

```mermaid
flowchart LR
  subgraph entry [Application Entry]
    A["/application?username=&job_offer_id="]
    B[Backend: Torre APIs]
    C[Persist + JobOfferApplied]
  end
  subgraph prep [Event Subscribers]
    D[GenerateCandidateEmbeddings]
    E[GenerateJobOfferEmbeddings]
    F[GenerateCallPrompt]
  end
  subgraph call [Call Flow]
    G["/call?application="]
    H[Consent]
    I[WebSocket + Emma Q&A]
    J[CallFinished]
  end
  subgraph analysis [Analysis]
    K[Analysis process]
    L["/analysis?application_id="]
  end
  A --> B --> C --> D
  C --> E
  C --> F
  C --> G --> H --> I --> J --> K --> L
```

---

## User Stories

### Phase 1 Stories

- **US1.1** — As a candidate, I want to open the app via `/application?username=...&job_offer_id=...` so that I can start the screening process.  
  **Acceptance**: Given valid query params, when the page loads, then the app shows the application flow (or loading). Given invalid/missing params, then the app shows an appropriate error or empty state.

- **US1.2** — As a candidate, I want to see a consent form before the call so that I can agree to the simulation.  
  **Acceptance**: Given I have been redirected to `/call?application=<id>`, when the page loads, then I see a consent form. When I have not accepted, then the call does not start. When I accept, then the call flow can start.

- **US1.3** — As a candidate, I want an audio-only call with Emma so that I can answer screening questions.  
  **Acceptance**: Given I have accepted consent, when the call starts, then I experience audio-only interaction (no video). I can hear Emma and respond; the UI shows connection/call state.

- **US1.4** — As a candidate, I want to be redirected to an analysis page after the call so that I can see my fit score and skills.  
  **Acceptance**: Given the call has ended, when the WebSocket closes, then a modal indicates the call ended and offers a button to go to the analysis page. When I click it, then I am redirected to `/analysis?application_id=...`.

- **US1.5** — As a candidate, I want the analysis page to show my fit score and skills when ready so that I understand the outcome.  
  **Acceptance**: Given I am on `/analysis?application_id=...`, when analysis is not ready, then a loading/waiting state is shown. When analysis is ready, then the fit score and skills are displayed.

### Phase 2 Stories

- **US2.1** — As the system, I want to fetch candidate and job data from Torre APIs and persist them so that the call and analysis can use them.  
  **Acceptance**: Given `username` and `job_offer_id`, when the application endpoint is called, then the backend calls Torre genome/bios and opportunities APIs, extracts full name/skills/jobs and objective/strengths/responsibilities, and persists. When an API returns an error, then the backend returns an error and the frontend can show “not found.”

- **US2.2** — As the system, I want to publish `JobOfferApplied` and run embedding and call-prompt generation so that the call has prepared questions and embeddings.  
  **Acceptance**: Given a new application has been persisted, when `JobOfferApplied` is published (with DB candidate_id and job_offer_id), then subscribers run GenerateCandidateEmbeddings, GenerateJobOfferEmbeddings, and GenerateCallPrompt.

- **US2.3** — As the system, I want a WebSocket call flow where Emma asks prepared questions and answers only role-related questions so that screening is consistent.  
  **Acceptance**: Given a call has started, when the WebSocket is open, then Emma greets, waits for candidate response (e.g. 5s), then runs a Q&A loop with prepared questions. When the candidate asks a question about the role, then Emma answers using job/role data only. When all questions are done, then Emma says goodbye and the WebSocket closes.

- **US2.4** — As the system, I want to run analysis when the call ends and store the result so that the analysis page can show the score.  
  **Acceptance**: Given the WebSocket has closed, when `CallFinished` is published, then a subscriber runs the analysis (fit score, skills) and persists the result for the given application.

### Phase 3 Stories

- **US3.1** — As a candidate, I want the frontend to use the application id and call/analysis APIs so that I can complete the full flow without manual steps.  
  **Acceptance**: Given I have submitted an application successfully, when the backend returns an application id, then I am redirected to `/call?application=<id>`. Given the call has ended, when I go to the analysis page, then the frontend fetches or polls until analysis is ready and displays the fit score and skills.

---

## Technical Considerations

- **Platform**: Web frontend (Vue.js); backend (Python/FastAPI); audio-only (no video).
- **Integration**: Torre public APIs — `GET https://torre.ai/api/genome/bios/<username>`, `GET https://torre.ai/api/suite/opportunities/<job_offer_id>`. Data extracted: from user — full name, skills (strengths), jobs; from job offer — objective, strengths, responsibilities (e.g. from details content).
- **Events**: `JobOfferApplied` (candidate_id, job_offer_id); `CallFinished` (after WebSocket close). See [bounded-context-structure.md](bounded-context-structure.md) for module communication.
- **Performance**: Real-time feel for call (low latency for Emma responses and audio streaming).
- **Security**: POC scope; no auth required for public Torre APIs; consent collected before call.
- **Suggested stack**: Frontend — Material Design, Tailwind, Vue.js. Backend — Python/FastAPI, Postgres, RAG (if needed), Ollama, RabbitMQ, Redis (if needed), Docker/Docker Compose. Architecture — hexagonal, event-driven.

---

## Constraints & Assumptions

- **Constraints**: Public Torre APIs only; POC scope; audio-only (no video); Emma answers only about the role.
- **Assumptions**: `username` and `job_offer_id` are derived from Torre URLs (e.g. torre.ai/<username>, torre.ai/post/<id>-...); one call per application; analysis runs asynchronously after call end; candidate and job offer data are stored in the project’s DB.
- **Risks**: Torre API rate limits or availability; LLM/voice latency affecting real-time feel.

---

## Timeline

- **Phase 1**: 2–3 weeks (or TBD).
- **Phase 2**: 3–4 weeks (or TBD).
- **Phase 3**: 1–2 weeks (or TBD).
- **Overall**: TBD until dates are set.

---

## Next Steps

1. Review and approve this PRD.
2. Create design doc(s) per phase (e.g. one per bounded-context module or per phase).
3. Implement following the bounded context structure (applications, calls, analysis). See [bounded-context-structure.md](bounded-context-structure.md).
4. Reference [screening-simulation-prompt.md](screening-simulation-prompt.md) for the original product prompt and flow details.
