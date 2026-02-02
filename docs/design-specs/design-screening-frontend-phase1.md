# Design Document: Screening Frontend — Phase 1

## Metadata

- **Related PRD**: [PRD: Screening Simulation (POC)](../prd-screening-simulation.md)
- **Phase**: Phase 1 — Frontend: Design System, Pages, Call Flow
- **Status**: Draft
- **Last Updated**: 2025-02-01
- **Author**: TBD
- **Reviewers**: TBD

---

## Overview

This design doc specifies the frontend for the Screening Simulation POC: a shared design system and the application, call, and analysis pages. The UI is built so the full user journey (application entry → consent → call → analysis) is defined and implementable with mock data and states, without backend dependency.

---

## Design System

The frontend uses a single design system for typography, color, and components. **Phase 1 adopts a custom design system (Mulish, custom color tokens, Tailwind, Vue.js) instead of Material Design as originally noted in the PRD.** Implement as design tokens (CSS variables or theme config) so Tailwind/Vue can consume them.

### Typography

**Font family**: [Mulish](https://fonts.google.com/share?selection.family=Mulish:ital,wght@0,200..1000;1,200..1000) (Google Fonts). Load as primary font for all UI.

| Name         | Size  | Weight   | Line Height | Use case                |
| ------------ | ----- | -------- | ----------- | ----------------------- |
| Display      | 64px  | Bold     | 72px        | Hero                    |
| H1           | 48px  | Bold     | 56px        | Main titles             |
| H2           | 36px  | Semibold | 44px        | Subtitles               |
| H3           | 24px  | Semibold | 32px        | Cards / components      |
| Body Large   | 18px  | Regular  | 28px        | Subheadlines            |
| Body         | 16px  | Regular  | 24px        | Main body text          |
| Body Small   | 14px  | Regular  | 20px        | Secondary text          |
| Button       | 16px  | Semibold | 24px        | Buttons                 |
| Caption      | 12px  | Regular  | 16px        | Timestamps, labels      |

**Implementation**: Expose token names (e.g. `--font-display`, `--text-body`) and map to Tailwind/utility classes or component props.

### Color Tokens

Use the following semantic color variables. Names use `-` (e.g. `background-0`). Map to CSS vars or theme object for Tailwind.

| Token                             | Value                     | Use case                         |
| --------------------------------- | ------------------------- | -------------------------------- |
| `background-0`                    | `#000`                    | Darkest background               |
| `background-05`                   | `#1c1d1f`                 | Near-black surface               |
| `background-1`                    | `#27292d`                 | Card/panel background            |
| `background-2`                    | `#383b40`                 | Elevated surface                 |
| `background-3`                    | `#5e626b`                 | Borders, subtle elements         |
| `text-primary`                    | `hsla(0, 0%, 100%, 0.9)`   | Primary text                     |
| `text-accent`                     | `hsla(0, 0%, 100%, 0.65)` | Secondary/accent text            |
| `text-disabled`                   | `hsla(0, 0%, 100%, 0.38)` | Disabled text                    |
| `text-primary-on-accent`         | `rgba(0, 0, 0, 0.9)`      | Text on brand/accent backgrounds |
| `warning`                         | `#ffd54f`                 | Warning state                    |
| `error`                           | `#cf6679`                 | Error state                      |
| `error-elevated`                  | `#ff8a8a`                 | Error on dark                    |
| `brand`                           | `#cddc39`                 | Primary brand / CTAs             |
| `disabled`                        | `hsla(0, 0%, 100%, 0.12)` | Disabled controls                |
| `badge`                           | `#ef5350`                 | Badges, alerts                   |
| `scrollbar`                       | `hsla(0, 0%, 100%, 0.25)` | Scrollbar thumb                  |
| `scrollbar-background`           | `rgba(0, 0, 0, 0.3)`      | Scrollbar track                  |
| `scrollbar-on-background-0`      | `hsla(0, 0%, 100%, 0.25)` | Scrollbar on background-0        |
| `scrollbar-background-on-background-0` | `rgba(0, 0, 0, 0.3)` | Scrollbar track on background-0  |
| `tooltip`                         | `#a9a9a9`                 | Tooltip background               |
| `divider`                         | `#5e626b`                 | Dividers, borders                |

### Design System Deliverables

- Typography scale and font (Mulish) wired to tokens/classes.
- Color tokens available globally (e.g. `tailwind.config` or CSS custom properties).
- Base components that use tokens: buttons, form inputs, cards, modals, loading states (design system scope; page-specific components are defined per feature below).

---

## Context

- **Problem**: Candidates need a clear, consistent UI to start a screening application, give consent, complete an audio-only call, and view analysis. The frontend must be buildable and testable without the backend.
- **Goals**: (1) Define and implement a reusable design system. (2) Implement application, call, and analysis pages with all required states (loading, error, empty, success). (3) Ensure consent blocks call start and that post-call navigation to analysis is explicit.
- **Scope**: In scope — design system; `/application` (query params, loading/error/not-found); redirect to `/call?application=<id>` on success; `/call` (consent form, call UI, post-call modal); `/analysis` (loading/waiting, fit score and skills when ready). Out of scope — real backend/WebSocket (use mocks); auth; video.

---

## Functional Specifications

### Feature 1: Design System

**Description**: Shared typography, colors, and base components so all pages look and behave consistently.

**User story**: N/A (foundation).

**Acceptance criteria**:

- All typography uses Mulish and the defined scale (Display through Caption).
- All UI uses the defined color tokens (no hardcoded hex outside tokens).
- Buttons, inputs, cards, and modals use tokens and are reusable across pages.

**Functional requirements**:

- FR-1.1: The app SHALL load Mulish from Google Fonts and apply it as the default font.
- FR-1.2: The app SHALL expose the typography scale as design tokens or utility classes.
- FR-1.3: The app SHALL expose the color palette as design tokens used by components and pages.
- FR-1.4: The app SHALL provide at least: primary button, secondary/outline button, text input, card container, modal, loading spinner/skeleton.

**Edge cases**:

- Font load failure: Fall back to system sans-serif; log or show no layout shift.
- Missing token: Define a single fallback (e.g. `text-primary` for unknown text) so nothing is invisible.

---

### Feature 2: Application Page

**Description**: Entry page at `/application` that reads `username` and `job_offer_id` from query params, shows loading/error/not-found states, and on successful application creation redirects to `/call?application=<application_id>`.

**User story**: US1.1 — As a candidate, I want to open the app via `/application?username=...&job_offer_id=...` so that I can start the screening process.

**Acceptance criteria** (from PRD):

- Given valid query params, when the page loads, the app shows the application flow (or loading).
- Given invalid/missing params, the app shows an appropriate error or empty state.

**Functional requirements**:

- FR-2.1: The app SHALL define a route `/application` that reads query params `username` and `job_offer_id`.
- FR-2.2: The app SHALL show a loading state while “creating” the application (mock: short delay then success).
- FR-2.3: The app SHALL show an error or not-found state when params are missing or invalid (e.g. empty `username` or `job_offer_id`).
- FR-2.4: The app SHALL show a success state when application “creation” succeeds (mock returns a fake `application_id`).
- FR-2.5: On successful application creation, the app SHALL redirect to `/call?application=<application_id>`.

**User flow**:

1. User lands on `/application?username=john&job_offer_id=abc123`.
2. Page shows loading (e.g. spinner or skeleton).
3. Mock “create application” resolves with `application_id`.
4. Redirect to `/call?application=<application_id>`.
5. Alternative: missing/invalid params → show error or empty state with clear message (no redirect).

**Edge cases**:

- Only one param present: Treat as invalid; show error state with message (e.g. “Username and job offer are required”).
- Malformed or unsafe query: Sanitize/validate; show error state.
- Redirect before load: If user navigates away during loading, cancel mock and do not redirect.

---

### Feature 3: Call Page — Consent and Call UI

**Description**: Page at `/call?application=<id>` that shows a consent form first, then (after accept) the audio-only call UI, and on call end shows a post-call modal with a button to go to analysis.

**User stories**: US1.2 (consent), US1.3 (audio-only call), US1.4 (redirect to analysis after call).

**Acceptance criteria** (from PRD):

- Given redirect to `/call?application=<id>`, when the page loads, the candidate sees a consent form.
- When the candidate has not accepted, the call does not start.
- When the candidate accepts, the call flow can start.
- Call is audio-only; UI shows connection/call state.
- When the call ends, a modal indicates the call ended and offers a button to the analysis page; clicking it redirects to `/analysis?application_id=...`.

**Functional requirements**:

- FR-3.1: The app SHALL define a route `/call` that reads query param `application` (application id).
- FR-3.2: The app SHALL show a consent form on load (e.g. checkbox + “I agree” and “Continue” button).
- FR-3.3: The app SHALL keep the “Start call” or call UI disabled or hidden until consent is accepted.
- FR-3.4: The app SHALL show call UI (audio-only, no video) after consent: connection state (e.g. connecting, connected, ended), mock duration/timer optional.
- FR-3.5: The app SHALL allow “ending” the call (mock button or auto-end after a short mock) and then show a post-call modal.
- FR-3.6: The post-call modal SHALL display a “Call ended” message and a button (e.g. “View analysis”) that navigates to `/analysis?application_id=<application_id>`.
- FR-3.7: If `application` is missing on `/call`, the app SHALL show an in-place error with a link to application or home; redirect to an application/error page is acceptable.
- FR-3.8: When the app displays any transcript or speech text received from the API (e.g. live transcript, candidate or Emma text), it SHALL strip or hide content between square brackets so that noise markers are not shown to the user. Examples of markers to remove: `[typing]`, `[background noise]`, `[cough]`, `[silence]`, or any `[ ... ]` segment. Display only the cleaned speech text.

**User flow**:

1. User arrives at `/call?application=xyz`.
2. Consent form is shown (copy about recording/use of data; checkbox; “Continue”).
3. User accepts → consent form is hidden, call UI is shown (e.g. “Connecting…” then “In call” with an “End call” button).
4. User ends call (or mock auto-ends) → modal: “Call ended” + “View analysis”.
5. User clicks “View analysis” → navigate to `/analysis?application_id=xyz`.

**Edge cases**:

- User refreshes after consent, before/during call: Re-show consent (no persistence in POC) or define simple rule (e.g. always show consent on load).
- Missing `application` in URL: Show error state and link back to application or home.
- User closes tab during call: No backend yet; optional local state cleanup.
- Transcript contains only bracketed segments (e.g. `[background noise]` with no speech): Show nothing or a neutral placeholder (e.g. “…”); do not display the raw brackets.

---

### Feature 4: Analysis Page

**Description**: Page at `/analysis?application_id=...` that shows a loading/waiting state until “analysis” is ready, then displays fit score and skills (mock data).

**User story**: US1.5 — As a candidate, I want the analysis page to show my fit score and skills when ready so that I understand the outcome.

**Acceptance criteria** (from PRD):

- Given user is on `/analysis?application_id=...`, when analysis is not ready, a loading/waiting state is shown.
- When analysis is ready, fit score and skills are displayed.

**Functional requirements**:

- FR-4.1: The app SHALL define a route `/analysis` that reads query param `application_id`.
- FR-4.2: The app SHALL show a loading or waiting state (e.g. spinner, “Analyzing your call…” or “Results will be ready shortly”) while analysis is “pending.”
- FR-4.3: The app SHALL show fit score and skills when analysis is “ready” (mock: delay 2–3 s then show fixed score and list of skills).
- FR-4.4: Fit score SHALL be in range 0–100, displayed as a percentage (e.g. 78%) using design system typography/colors.
- FR-4.5: Skills SHALL be displayed as a list or set of tags (e.g. Body or Body Small, optional badge color).
- FR-4.6: If `application_id` is missing, the app SHALL show an error or redirect.

**User flow**:

1. User lands on `/analysis?application_id=xyz`.
2. Page shows loading/waiting state.
3. After mock delay, show fit score (e.g. 78%) and skills (e.g. “Python”, “Communication”, “Problem solving”).
4. User can read the result; no further action required for POC.

**Edge cases**:

- Missing `application_id`: Show error and link back.
- “Analysis failed” (mock): Show error message and link to application; retry is out of scope for POC.

---

## Technical Design

### Architecture

- **Stack**: Vue.js (SPA), Vue Router, Tailwind CSS (or equivalent) consuming design tokens. No backend dependency for Phase 1; use in-memory or static mocks.
- **Routing**: SPA with routes: `/application`, `/call`, `/analysis`. Query params drive state and mocks.
- **State**: Per-page component state or Pinia (optional) for consent and mock “application id” / “analysis ready” flags. No persistence required.

### Components

| Component           | Responsibility                                                                 |
| ------------------- | ------------------------------------------------------------------------------ |
| App shell           | Router view, global layout, font and token injection                          |
| Design token provider | CSS variables or Tailwind theme from design system (typography + colors)     |
| ApplicationPage     | Parse query params; loading/error/success; redirect to `/call` on success      |
| CallPage            | Consent form; call UI (states); post-call modal; navigate to `/analysis`       |
| AnalysisPage        | Loading state; fit score and skills display                                    |
| ConsentForm         | Checkbox, copy, primary button; emit “accepted”                                 |
| CallUI              | Connection state, end-call button (mock), optional timer; when displaying transcript/API text, strip bracketed noise markers (e.g. `[typing]`, `[background noise]`) |
| PostCallModal       | “Call ended” message, “View analysis” button                                  |
| FitScoreDisplay     | Score value and label (design system typography)                               |
| SkillsList          | List or tags of skills (Body Small / Caption, optional badge)                  |

### Data Models (Frontend)

Mock types for Phase 1; align with backend DTOs in Phase 3.

```typescript
// Mock / types for Phase 1
interface ApplicationParams {
  username: string;
  job_offer_id: string;
}

interface ApplicationResult {
  application_id: string;
}

interface CallState {
  status: 'idle' | 'connecting' | 'connected' | 'ended';
  applicationId: string | null;
}

interface AnalysisResult {
  fit_score: number;  // 0–100, display as percentage
  skills: string[];
}

// Route query types
// /application?username=&job_offer_id=
// /call?application=
// /analysis?application_id=
```

### APIs / Interfaces (Mock)

- **Create application** (mock): Input `username`, `job_offer_id`; delay ~800 ms; return `{ application_id: string }`. Invalid params → reject with error message.
- **Call** (mock): No real WebSocket; “Start call” sets state to connected; “End call” or timeout sets state to ended and opens post-call modal.
- **Get analysis** (mock): Input `application_id`; delay ~2–3 s; return `{ fit_score: number (0–100), skills: string[] }`.

### Design Decisions

**Decision 1: Design tokens (typography + colors)**  
- **Context**: Need consistent UI and a single source of truth for Mulish and the provided palette.  
- **Options**: Hardcoded classes; Tailwind config only; CSS variables + Tailwind.  
- **Chosen**: CSS custom properties (and/or Tailwind theme) generated from the design system table and color list.  
- **Rationale**: Enables theme consistency and future tweaks in one place.  
- **Trade-off**: Slight setup cost vs. long-term consistency.

**Decision 2: Consent blocks call in UI only**  
- **Context**: PRD requires that the call does not start until the user accepts.  
- **Chosen**: Call UI and “Start call” are disabled or not rendered until consent is accepted; no backend in Phase 1.  
- **Rationale**: Meets acceptance criteria and keeps Phase 1 frontend-only.

**Decision 3: Mock delays and fixed data**  
- **Context**: Backend and WebSocket are Phase 2.  
- **Chosen**: Timeouts and fixed mock responses for application creation, call state, and analysis.  
- **Rationale**: Allows full navigation and state flow testing without backend.  
- **Trade-off**: Replace mocks in Phase 3 with real API/WebSocket.

---

## Implementation Plan

### Tasks

1. [ ] **Design system**
   - [ ] Add Mulish (Google Fonts) and typography tokens/classes.
   - [ ] Add color tokens (CSS variables or Tailwind theme).
   - [ ] Implement base components: button (primary/secondary), input, card, modal, loading spinner/skeleton.
2. [ ] **Routing and app shell**
   - [ ] Vue Router with routes: `/application`, `/call`, `/analysis`.
   - [ ] App shell with router-view and global styles (tokens).
3. [ ] **Application page**
   - [ ] Read `username` and `job_offer_id` from query; validate.
   - [ ] Loading state; mock create application; error/not-found state.
   - [ ] Redirect to `/call?application=<id>` on success.
4. [ ] **Call page**
   - [ ] Read `application` from query; error if missing.
   - [ ] Consent form component; gate call UI on consent.
   - [ ] Call UI with connection state and mock “End call.”
   - [ ] Post-call modal with “View analysis” → `/analysis?application_id=...`.
5. [ ] **Analysis page**
   - [ ] Read `application_id` from query; error if missing.
   - [ ] Loading/waiting state; mock analysis result after delay.
   - [ ] Fit score and skills display using design system.
6. [ ] **Copy and accessibility**
   - [ ] Consent copy (placeholder or final); aria labels and focus order for forms and modals.

### Dependencies

- **Requires**: None (frontend-only, mock data).
- **Blocks**: Phase 3 integration (real API and WebSocket will replace mocks).

### Testing Strategy

- **Unit**: Validation of query params; redirect logic; consent gating (call not startable until accept).
- **Component**: ConsentForm, PostCallModal, FitScoreDisplay, SkillsList with design system and tokens.
- **E2E**: Recommended for happy path (application → consent → call → end call → analysis) and key error paths (missing params on each route). Manual verification only is acceptable for POC if E2E is not implemented.

---

## Non-Functional Requirements

- **Performance**: First contentful paint and interactivity within 2–3 s on mid-range devices; font and token load should not block render (e.g. font-display: swap).
- **Accessibility**: Semantic HTML, focus management in modals, sufficient contrast (use `text-primary` / `text-accent` on defined backgrounds).
- **Responsiveness**: Layout works on viewports ≥360px width; typography and spacing scale with design system.

---

## Success Metrics

- All routes and UI states (loading, error, not-found, success) are implementable from this spec.
- Design system is consistent: Mulish, typography scale, and color tokens used across all pages.
- Consent blocks call start until accepted (verified by test or manual check).
- A user can complete the flow application → consent → call → end call → analysis using only the frontend and mocks.

---

## References

- PRD: [docs/prd-screening-simulation.md](../prd-screening-simulation.md) — Phase 1
- Bounded context: [docs/bounded-context-structure.md](../bounded-context-structure.md)
- Font: [Mulish — Google Fonts](https://fonts.google.com/share?selection.family=Mulish:ital,wght@0,200..1000;1,200..1000)
