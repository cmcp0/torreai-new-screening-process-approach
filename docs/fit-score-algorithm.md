# Fit-Score Algorithm

This document describes how the screening fit-score (0–100) is computed and when fallbacks apply.

## Overview

The fit-score is a 0–100 value indicating how well a candidate matches the job offer, derived from the screening call transcript and optional embedding similarity.

## When Embeddings Are Available

When both candidate and job-offer embeddings exist (Ollama configured and `JobOfferApplied` handlers have run successfully):

1. **Cosine similarity** between the candidate embedding vector and the job-offer embedding vector is computed.
2. Cosine similarity is in the range `[-1, 1]`. It is mapped to 0–100 with:
   - `score = round((cos + 1) / 2 * 100)`
   - Clamped to `[0, 100]`.
3. This score is used as the fit-score. Skills are still derived from the transcript (job strengths mentioned by the candidate, or candidate skills as fallback).

## Fallback When Embeddings Are Missing

When embeddings are not configured or not yet computed for the application:

1. A **rule-based** score is used:
   - Base: `40 + len(transcript) * 5 + len(matched_skills) * 10`
   - Capped at 100.
2. **Skills** are:
   - Job strengths (from the job offer) that appear in the candidate’s transcript, or
   - Up to 5 candidate skills if no job-strength matches are found.

If the transcript is too short (e.g. fewer than 2 segments) or has no candidate text, the score is 0 and skills may be empty.

## Embedding Model and Dimension

- **Model**: Configured via `SCREENING_OLLAMA_EMBED_MODEL` (default: `nomic-embed-text`). See `src/config.py`.
- **Dimension**: Determined by the model (e.g. nomic-embed-text typically produces 768 dimensions). The analysis service assumes both candidate and job-offer vectors have the **same length** for cosine similarity; if you change the embed model, ensure both embeddings use the same model or validate dimension consistency.
- **Persistence**: Embeddings are stored in the `entity_embeddings` table (or in-memory when no DB is configured) and associated with candidate_id and job_offer_id per FR-2.1/FR-2.2.

## Implementation Reference

- **Service**: `src/screening/analysis/application/services/analysis_service.py` — see `_compute_fit_score_and_skills` and its docstring.
- **Embeddings**: `src/screening/applications/infrastructure/subscribers/embeddings.py` — candidate and job-offer text are embedded on `JobOfferApplied`; results are persisted (when DB is configured) and read by the analysis service when present.
