# Screening Simulation POC — Product Prompt

This document stores the product prompt for the Screening Simulation POC (Software Development Contributor role at Torre.ai), with grammatical corrections applied.

---

## Product Prompt

A simulation of a screening process for a candidate who applies to a job offer. This is a POC for the Software Development Contributor role at Torre.ai.

We want to build an **audio-only call simulation** where Emma (Torre.ai’s AI agent) asks the candidate prepared questions for their screening interview. Emma can answer the candidate’s questions but only about the role.

### Simulation Flow

1. The frontend accepts requests from the URI `/application?username=*****&job_offer_id=*****`.

   Example URLs:
   - User URL: `https://torre.ai/carlosmariocacerespalacio?r=GLmJKv0B`
   - Job offer post URL: `https://torre.ai/post/NwqBEBkd-torreai-software-development-contributor-in-exchange-for-equity-no-cash-4`

   So the request is: `/application?username=carlosmariocacerespalacio&job_offer_id=NwqBEBkd`

2. This request goes to the backend, which uses those parameters to call these public APIs:
   - `GET https://torre.ai/api/genome/bios/<username>`
   - `GET https://torre.ai/api/suite/opportunities/<job_offer_id>`

   Example:
   - `curl https://torre.ai/api/genome/bios/carlosmariocacerespalacio`
   - `curl https://torre.ai/api/suite/opportunities/NwqBEBkd`

3. If the backend returns any error, the frontend can show a “not found” message.

4. If the backend successfully requests user and job offer data:
   - **From user**: extract full name, skills (strengths), and jobs.
   - **From job offer**: extract objective, strengths, and responsibilities.

5. The backend saves this data into the database.

6. Create an event `JobOfferApplied` sending the DB’s `candidate_id` and `job_offer_id`.

7. Commands subscribe to this event:
   - **GenerateCandidateEmbeddings** (full_name, skills, jobs) — to generate embedding vectors for the Candidate model’s embedding field.
   - **GenerateJobOfferEmbeddings** (objective, strengths, responsibilities) — to generate embedding vectors for the JobOffer model’s embedding field.
   - **GenerateCallPrompt** — to generate the call’s template with prepared questions for the call.

8. For a successful response, the backend returns an application id.

9. The frontend uses this application id to redirect to `/call?application=******`.

10. Before starting, show a consent form that the user must accept to continue.

11. Once the user has accepted the terms and conditions, the call flow starts.

12. The backend opens a WebSocket to start streaming data to the frontend.

    **Call flow:**
    - 12.1. Emma’s greeting.
    - 12.2. Emma waits for any candidate response (e.g. 5s).
    - 12.3. Then the conversation loop of Q&A between Emma and the candidate starts.
    - 12.4. Some of the candidate’s responses may be questions; Emma tries to fetch info from the DB to answer them.
    - 12.5. Emma continues asking questions.
    - 12.6. When Emma has finished asking questions, Emma ends the call and says goodbye.

13. After the call has finished, the WebSocket must close. This event triggers a modal saying that the call ended. The modal shows a button for the next step of the simulation; this button redirects to an analysis page.

14. On the backend, after the socket is closed, the event `CallFinished` is sent. A command subscriber runs to start an analysis process that produces the fit score of the candidate for the job offer.

15. `/analysis?application_id=****` is the path for the analysis page. If analysis is not ready, show a waiting/loading state.

16. On the analysis page, display the candidate’s fit score for the role and skills.

17. End.

### Implementation Phases

1. **Frontend**: Design system, pages, call flow.
2. **Backend**: Services, call flow.
3. **Integration**.

### Suggested Stack

- **Frontend**: Material Design, Tailwind, Vue.js.
- **Backend**: Python/FastAPI, Postgres, RAG, Ollama, RabbitMQ, Redis (if needed), Docker/Docker Compose.
- **Architecture**: Hexagonal, event-driven.
