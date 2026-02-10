# Torre API Paths

This document records the Torre.ai API paths used by the screening backend and how they are configured.

## Paths in use

- **Bios (candidate profile)**: `GET {base}/api/genome/bios/{username}`
  - Used to fetch candidate data by Torre username.
- **Opportunities (job offer)**: `GET {base}/api/suite/opportunities/{job_offer_id}`
  - Used to fetch job offer details by job offer ID.

These paths match the current Torre public API. The backend does not use authentication for this POC.

## Environment override

- **Base URL**: Set via `SCREENING_TORRE_BASE_URL`. Default: `https://torre.ai`.
- Use a different base URL for staging or alternate Torre environments (e.g. `https://staging.torre.ai`).

Other Torre-related settings (see `src/config.py`): `SCREENING_TORRE_TIMEOUT`, `SCREENING_TORRE_RETRIES`.
