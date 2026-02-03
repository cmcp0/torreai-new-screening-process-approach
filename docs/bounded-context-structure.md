# Bounded Context Structure: Screening

## Overview

The `screening` bounded context is organized into **modules** to maintain Single Responsibility Principle (SRP) and clear boundaries within the context.

## Bounded Context Location

Bounded contexts are located **directly in `/src/`**. The structure is:
- `/src/` contains bounded contexts (e.g., `src/screening/`)
- Each bounded context contains modules (e.g., `src/screening/applications/`)
- Future bounded contexts would be added as siblings (e.g., `src/notifications/`, `src/analytics/`)

## Module Structure

Within the `screening` bounded context, we have three modules:

### 1. `applications/` Module

**Responsibility**: Application submission and event handling

**Domain**:
- `ScreeningApplication` entity
- `JobOfferApplied` domain event
- Application validation rules

**Application**:
- `ApplicationService` - Handles application submission
- Commands for creating applications

**Infrastructure**:
- Event publisher adapters
- Application repository implementations

**Features**:
- Feature 1.1: Application Form
- Feature 1.2: Application Submission Event

---

### 2. `calls/` Module

**Responsibility**: Call management, execution, and real-time processing

**Domain**:
- `ScreeningCall` entity
- `CallStatus` value object
- `UserLeftCall` domain event
- Call business rules

**Application**:
- `CallService` - Manages call lifecycle
- `EmmaService` - Handles Emma AI interactions
- Commands for call initiation, management

**Infrastructure**:
- `OpenRouterLLMAdapter` - LLM provider implementation
- `ElevenLabsTranscriptionAdapter` - STT/TTS implementation
- `WebRTCAdapter` - Video/audio handling

**Features**:
- Feature 3.1: Call Page Transition
- Feature 3.2: Consent Collection
- Feature 4.1: Call Initiation
- Feature 4.2: Screening Interview Execution
- Feature 4.3: Real-Time Data Persistence
- Feature 4.4: Candidate Q&A Handling
- Feature 5.1: Call Closure Sequence
- Feature 5.2: User Exit Event

---

### 3. `analysis/` Module

**Responsibility**: Post-call analysis, embeddings, and scoring

**Domain**:
- `ScreeningAnalysis` entity
- `FitAssessment` value object
- `AnalysisCompleted` domain event
- Analysis business rules

**Application**:
- `AnalysisService` - Orchestrates analysis workflow
- Commands for triggering analysis

**Infrastructure**:
- `OpenRouterEmbeddingsAdapter` - Embeddings provider
- Analysis repository implementations

**Features**:
- Feature 6.1: Call Analysis Processing
- Feature 6.2: Results Display Page

---

## Module Communication

Modules communicate through:
1. **Domain Events**: Published by one module, consumed by another
   - `JobOfferApplied` (applications) → triggers data prep
   - `UserLeftCall` (calls) → triggers analysis
   - `AnalysisCompleted` (analysis) → enables results display

2. **Shared Domain Concepts**: Some concepts may be shared (e.g., `ApplicationId`)
   - Shared concepts used across multiple bounded contexts go in `src/shared/domain/`
   - Concepts only used within `screening` context stay in the context's modules

3. **Application Services**: Can coordinate across modules when needed

## Shared Code

### Global Shared Code (`src/shared/`)

Code that is used across **multiple bounded contexts** should be placed in `src/shared/`:

- **`shared/domain/`**: Shared domain concepts
  - Common value objects (e.g., `Email`, `UserId`, `Timestamp`) used across contexts
  - Shared domain types and enums
  - Base domain exceptions

- **`shared/application/`**: Shared application utilities
  - Base service classes
  - Common DTOs used across contexts
  - Shared validation utilities

- **`shared/infrastructure/`**: Shared infrastructure code
  - Base adapter classes
  - Common infrastructure utilities (logging, retry logic, etc.)
  - Shared configuration helpers

**Guideline**: Only add code to `src/shared/` if it's used by multiple bounded contexts.

### Context-Level Shared Code (`src/screening/shared/`)

**Optional**: The `screening` bounded context can have its own `shared/` folder for code shared across modules within the context:

- **`screening/shared/domain/`**: Domain concepts shared across modules
  - Context-specific value objects (e.g., `ApplicationId`, `ScreeningStatus`) used by multiple modules
  - Shared domain types within the screening context
  - Context-specific domain exceptions

- **`screening/shared/application/`**: Application utilities shared across modules
  - Context-specific base services
  - Common DTOs used by multiple modules in the screening context
  - Shared validation logic within the context

- **`screening/shared/infrastructure/`**: Infrastructure code shared across modules
  - Context-specific base adapters
  - Common utilities used by multiple modules

**Guidelines**:
- **Optional**: Only create `src/screening/shared/` if modules share significant code
- Use when multiple modules need the same utilities/concepts within the context
- If code is only used by one module, keep it in that module
- If code might be used by other bounded contexts, consider `src/shared/` instead

## SOLID Principles in Module Structure

### Single Responsibility Principle (SRP)
- Each module has a single, well-defined responsibility
- `applications/` handles applications only
- `calls/` handles calls only
- `analysis/` handles analysis only

### Dependency Inversion Principle (DIP)
- Modules depend on domain abstractions (ports), not each other
- Communication via domain events (loose coupling)
- Infrastructure adapters are swappable

### Open/Closed Principle (OCP)
- New modules can be added without modifying existing ones
- New event handlers can be added without changing event publishers

## Application / framework boundary

- **`src/`** holds only business logic (screening bounded context, shared domain, config, wiring). No HTTP or FastAPI.
- **`apps/backend/`** holds the FastAPI app: routes, request/response schemas (Pydantic), and `main.py`. It depends on `src` for services and wiring. Run with `uvicorn apps.backend.main:app` or `python -m apps.backend`.

## Directory Structure

```
src/screening/
├── applications/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── screening_application.py
│   │   ├── events/
│   │   │   └── job_offer_applied.py
│   │   └── ports/
│   │       └── event_publisher.py
│   ├── application/
│   │   └── services/
│   │       └── application_service.py
│   └── infrastructure/
│       └── adapters/
│           └── rabbitmq_event_publisher.py
├── calls/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── screening_call.py
│   │   ├── value_objects/
│   │   │   └── call_status.py
│   │   ├── events/
│   │   │   └── user_left_call.py
│   │   └── ports/
│   │       ├── llm_provider.py
│   │       └── transcription_provider.py
│   ├── application/
│   │   └── services/
│   │       ├── call_service.py
│   │       └── emma_service.py
│   └── infrastructure/
│       └── adapters/
│           ├── openrouter_llm_adapter.py
│           └── elevenlabs_transcription_adapter.py
└── analysis/
    ├── domain/
    │   ├── entities/
    │   │   └── screening_analysis.py
    │   ├── value_objects/
    │   │   └── fit_assessment.py
    │   ├── events/
    │   │   └── analysis_completed.py
    │   └── ports/
    │       └── embeddings_provider.py
    ├── application/
    │   └── services/
    │       └── analysis_service.py
    └── infrastructure/
        └── adapters/
            └── openrouter_embeddings_adapter.py
```

## Data Preparation

**Question**: Where does data preparation (fetching Torre.ai APIs, generating Emma prompts) go?

**Answer**: Data preparation is a **cross-cutting concern** that could be:
1. **Option A**: Separate module `data_preparation/` (if it's complex enough)
2. **Option B**: Part of `applications/` module (since it's triggered by `JobOfferApplied`)
3. **Option C**: Shared service in `screening/` root (if used by multiple modules)

**Recommendation for POC**: **Option B** - Keep it in `applications/` module since it's directly triggered by application submission and prepares data for calls.

---

## Future Considerations

If the system grows, potential new modules or bounded contexts:

**Within `screening` bounded context**:
- `data_preparation/` - If data prep becomes complex enough
- `notifications/` - If email/SMS notifications are added

**New bounded contexts**:
- `notifications/` - If notifications become a separate domain
- `analytics/` - If advanced analytics/reporting is needed
- `user_management/` - If authentication/authorization is added

---

*This structure follows DDD principles: bounded contexts contain modules, modules contain layers (domain/application/infrastructure).*
