import logging
from typing import Any, Optional

import httpx

from src.screening.applications.domain.ports import TorreBiosPort
from src.screening.applications.domain.value_objects import CandidateFromTorre

logger = logging.getLogger(__name__)


class TorreBiosAdapter(TorreBiosPort):
    def __init__(
        self,
        base_url: str = "https://torre.ai",
        timeout: float = 5.0,
        retries: int = 1,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retries = retries

    async def get_bio(self, username: str) -> Optional[CandidateFromTorre]:
        url = f"{self._base_url}/api/genome/bios/{username}"
        last_exc: Optional[Exception] = None
        for attempt in range(self._retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url)
                    if response.status_code == 404:
                        return None
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_bio(username, data)
            except httpx.HTTPStatusError as e:
                last_exc = e
                if e.response.status_code == 404:
                    return None
                if attempt < self._retries:
                    continue
                raise
            except (httpx.RequestError, ValueError) as e:
                last_exc = e
                if attempt < self._retries:
                    continue
                raise
        if last_exc:
            raise last_exc
        return None

    def _parse_bio(self, username: str, data: dict) -> Optional[CandidateFromTorre]:
        try:
            person = data.get("person") or {}
            full_name = (
                person.get("name")
                or f"{person.get('firstName', '')} {person.get('lastName', '')}".strip()
                or username
            )
            strengths = data.get("strengths") or []
            skills = [s.get("name") or str(s) for s in strengths if isinstance(s, dict)]
            if not skills and isinstance(strengths[0], str) if strengths else False:
                skills = list(strengths)
            jobs = data.get("experience") or data.get("jobs") or []
            if isinstance(jobs, list) and jobs and isinstance(jobs[0], dict):
                jobs = [{"title": j.get("name") or j.get("title"), "organization": j.get("organization")} for j in jobs[:20]]
            else:
                jobs = []
            return CandidateFromTorre(
                username=username,
                full_name=full_name or username,
                skills=skills,
                jobs=jobs,
            )
        except (KeyError, TypeError, IndexError) as e:
            logger.warning("Torre bios parse error for %s: %s", username, e)
            return None
