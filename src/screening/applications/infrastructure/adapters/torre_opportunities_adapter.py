import logging
import re
from typing import Any, Optional

import httpx

from src.screening.applications.domain.ports import TorreOpportunitiesPort
from src.screening.applications.domain.value_objects import JobOfferFromTorre

logger = logging.getLogger(__name__)


class TorreOpportunitiesAdapter(TorreOpportunitiesPort):
    def __init__(
        self,
        base_url: str = "https://torre.ai",
        timeout: float = 5.0,
        retries: int = 1,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retries = retries

    async def get_opportunity(self, job_offer_id: str) -> Optional[JobOfferFromTorre]:
        url = f"{self._base_url}/api/suite/opportunities/{job_offer_id}"
        last_exc: Optional[Exception] = None
        for attempt in range(self._retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url)
                    if response.status_code == 404:
                        return None
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_opportunity(job_offer_id, data)
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

    def _parse_opportunity(
        self, external_id: str, data: dict
    ) -> Optional[JobOfferFromTorre]:
        try:
            objective = data.get("objective") or ""
            details = data.get("details") or []
            strengths: list[str] = []
            responsibilities: list[str] = []
            if isinstance(details, list):
                for d in details:
                    if not isinstance(d, dict):
                        continue
                    code = (d.get("code") or "").upper()
                    content = d.get("content") or ""
                    if code == "STRENGTHS" or "strength" in (d.get("code") or "").lower():
                        strengths = self._split_lines(content)
                    elif code == "RESPONSIBILITIES" or "responsibilit" in (d.get("code") or "").lower():
                        responsibilities = self._split_lines(content)
            if not strengths and isinstance(data.get("strengths"), list):
                strengths = [s.get("name") or str(s) for s in data["strengths"] if isinstance(s, dict)]
            return JobOfferFromTorre(
                external_id=external_id,
                objective=objective,
                strengths=strengths,
                responsibilities=responsibilities,
            )
        except (KeyError, TypeError) as e:
            logger.warning("Torre opportunity parse error for %s: %s", external_id, e)
            return None

    @staticmethod
    def _split_lines(content: str) -> list[str]:
        if not content:
            return []
        lines = re.split(r"[\n•·]", content)
        return [s.strip() for s in lines if s.strip()][:50]
