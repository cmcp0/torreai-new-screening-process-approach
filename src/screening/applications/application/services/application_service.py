from datetime import datetime
from uuid import uuid4

from src.screening.applications.domain.entities import (
    Candidate,
    JobOffer,
    ScreeningApplication,
)
from src.screening.applications.domain.events import JobOfferApplied
from src.screening.applications.domain.ports import (
    EventPublisher,
    TorreBiosPort,
    TorreOpportunitiesPort,
)
from src.screening.applications.application.ports import ApplicationRepository
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


class CreateApplicationResult:
    def __init__(self, application_id: ApplicationId, created: bool) -> None:
        self.application_id = application_id
        self.created = created


class ApplicationService:
    def __init__(
        self,
        bios: TorreBiosPort,
        opportunities: TorreOpportunitiesPort,
        repository: ApplicationRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._bios = bios
        self._opportunities = opportunities
        self._repository = repository
        self._event_publisher = event_publisher

    async def create_application(
        self, username: str, job_offer_id: str
    ) -> CreateApplicationResult:
        username = (username or "").strip()
        job_offer_id = (job_offer_id or "").strip()
        if not username or not job_offer_id:
            raise ValueError("username and job_offer_id are required")

        existing = await self._repository.find_application_by_username_and_job_offer(
            username, job_offer_id
        )
        if existing is not None:
            return CreateApplicationResult(application_id=existing.id, created=False)

        bio = await self._bios.get_bio(username)
        if bio is None:
            raise TorreNotFoundError("Candidate not found")

        opportunity = await self._opportunities.get_opportunity(job_offer_id)
        if opportunity is None:
            raise TorreNotFoundError("Job offer not found")

        candidate_id = CandidateId(uuid4())
        candidate = Candidate(
            id=candidate_id,
            username=bio.username,
            full_name=bio.full_name,
            skills=bio.skills,
            jobs=bio.jobs,
        )
        await self._repository.save_candidate(candidate)

        job_offer_id_entity = JobOfferId(uuid4())
        job_offer = JobOffer(
            id=job_offer_id_entity,
            external_id=opportunity.external_id,
            objective=opportunity.objective,
            strengths=opportunity.strengths,
            responsibilities=opportunity.responsibilities,
        )
        await self._repository.save_job_offer(job_offer)

        application_id = ApplicationId(uuid4())
        application = ScreeningApplication(
            id=application_id,
            candidate_id=candidate_id,
            job_offer_id=job_offer_id_entity,
            created_at=datetime.utcnow(),
        )
        await self._repository.save_application(application)

        event = JobOfferApplied(
            candidate_id=candidate_id,
            job_offer_id=job_offer_id_entity,
            application_id=application_id,
            occurred_at=datetime.utcnow(),
        )
        self._event_publisher.publish(event)

        return CreateApplicationResult(application_id=application_id, created=True)


class TorreNotFoundError(Exception):
    pass
