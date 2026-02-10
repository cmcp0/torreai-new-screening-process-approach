import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func

from src.screening.applications.application.ports import ApplicationRepository
from src.screening.applications.domain.entities import (
    Candidate,
    JobOffer,
    ScreeningApplication,
)
from src.screening.persistence.models import (
    ApplicationModel,
    CandidateModel,
    JobOfferModel,
)
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


def _candidate_to_entity(row: CandidateModel) -> Candidate:
    return Candidate(
        id=CandidateId(row.id),
        username=row.username,
        full_name=row.full_name,
        skills=row.skills if isinstance(row.skills, list) else [],
        jobs=row.jobs if isinstance(row.jobs, list) else [],
    )


def _job_offer_to_entity(row: JobOfferModel) -> JobOffer:
    return JobOffer(
        id=JobOfferId(row.id),
        external_id=row.external_id,
        objective=row.objective,
        strengths=row.strengths if isinstance(row.strengths, list) else [],
        responsibilities=row.responsibilities if isinstance(row.responsibilities, list) else [],
    )


def _application_to_entity(row: ApplicationModel, candidate: Optional[Candidate], job_offer: Optional[JobOffer]) -> ScreeningApplication:
    return ScreeningApplication(
        id=ApplicationId(row.id),
        candidate_id=CandidateId(row.candidate_id),
        job_offer_id=JobOfferId(row.job_offer_id),
        created_at=row.created_at,
    )


class PostgresApplicationRepository(ApplicationRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def _find_application_by_username_and_job_offer_sync(
        self, username: str, job_offer_id: str
    ) -> Optional[ScreeningApplication]:
        key_username = username.strip().lower()
        key_job = job_offer_id.strip()
        with self._session_factory() as session:
            app_row = (
                session.execute(
                    select(ApplicationModel)
                    .join(CandidateModel, ApplicationModel.candidate_id == CandidateModel.id)
                    .join(JobOfferModel, ApplicationModel.job_offer_id == JobOfferModel.id)
                    .where(
                        func.lower(CandidateModel.username) == key_username,
                        JobOfferModel.external_id == key_job,
                    )
                )
                .scalars()
                .first()
            )
            if app_row is None:
                return None
            cand = session.get(CandidateModel, app_row.candidate_id)
            job = session.get(JobOfferModel, app_row.job_offer_id)
            return _application_to_entity(
                app_row,
                _candidate_to_entity(cand) if cand else None,
                _job_offer_to_entity(job) if job else None,
            )

    async def find_application_by_username_and_job_offer(
        self, username: str, job_offer_id: str
    ) -> Optional[ScreeningApplication]:
        return await asyncio.to_thread(
            self._find_application_by_username_and_job_offer_sync, username, job_offer_id
        )

    def _save_candidate_sync(self, candidate: Candidate) -> CandidateId:
        with self._session_factory() as session:
            row = CandidateModel(
                id=candidate.id.value,
                username=candidate.username,
                full_name=candidate.full_name,
                skills=candidate.skills,
                jobs=candidate.jobs,
            )
            session.merge(row)
            session.commit()
        return candidate.id

    async def save_candidate(self, candidate: Candidate) -> CandidateId:
        return await asyncio.to_thread(self._save_candidate_sync, candidate)

    def _save_job_offer_sync(self, job_offer: JobOffer) -> JobOfferId:
        with self._session_factory() as session:
            row = JobOfferModel(
                id=job_offer.id.value,
                external_id=job_offer.external_id,
                objective=job_offer.objective,
                strengths=job_offer.strengths,
                responsibilities=job_offer.responsibilities,
            )
            session.merge(row)
            session.commit()
        return job_offer.id

    async def save_job_offer(self, job_offer: JobOffer) -> JobOfferId:
        return await asyncio.to_thread(self._save_job_offer_sync, job_offer)

    def _save_application_sync(self, application: ScreeningApplication) -> ApplicationId:
        with self._session_factory() as session:
            row = ApplicationModel(
                id=application.id.value,
                candidate_id=application.candidate_id.value,
                job_offer_id=application.job_offer_id.value,
                created_at=application.created_at,
            )
            session.merge(row)
            session.commit()
        return application.id

    async def save_application(
        self, application: ScreeningApplication
    ) -> ApplicationId:
        return await asyncio.to_thread(self._save_application_sync, application)

    def _save_application_graph_sync(
        self,
        candidate: Candidate,
        job_offer: JobOffer,
        application: ScreeningApplication,
    ) -> ApplicationId:
        with self._session_factory() as session:
            session.merge(
                CandidateModel(
                    id=candidate.id.value,
                    username=candidate.username,
                    full_name=candidate.full_name,
                    skills=candidate.skills,
                    jobs=candidate.jobs,
                )
            )
            session.merge(
                JobOfferModel(
                    id=job_offer.id.value,
                    external_id=job_offer.external_id,
                    objective=job_offer.objective,
                    strengths=job_offer.strengths,
                    responsibilities=job_offer.responsibilities,
                )
            )
            session.merge(
                ApplicationModel(
                    id=application.id.value,
                    candidate_id=application.candidate_id.value,
                    job_offer_id=application.job_offer_id.value,
                    created_at=application.created_at,
                )
            )
            session.commit()
        return application.id

    async def save_application_graph(
        self,
        candidate: Candidate,
        job_offer: JobOffer,
        application: ScreeningApplication,
    ) -> ApplicationId:
        return await asyncio.to_thread(
            self._save_application_graph_sync,
            candidate,
            job_offer,
            application,
        )

    def _get_application_sync(self, application_id: ApplicationId) -> Optional[ScreeningApplication]:
        with self._session_factory() as session:
            row = session.get(ApplicationModel, application_id.value)
            if row is None:
                return None
            cand = session.get(CandidateModel, row.candidate_id)
            job = session.get(JobOfferModel, row.job_offer_id)
            return _application_to_entity(
                row,
                _candidate_to_entity(cand) if cand else None,
                _job_offer_to_entity(job) if job else None,
            )

    async def get_application(self, application_id: ApplicationId) -> Optional[ScreeningApplication]:
        return await asyncio.to_thread(self._get_application_sync, application_id)

    def get_candidate(self, candidate_id: CandidateId) -> Optional[Candidate]:
        with self._session_factory() as session:
            row = session.get(CandidateModel, candidate_id.value)
            return _candidate_to_entity(row) if row else None

    def get_job_offer(self, job_offer_id: JobOfferId) -> Optional[JobOffer]:
        with self._session_factory() as session:
            row = session.get(JobOfferModel, job_offer_id.value)
            return _job_offer_to_entity(row) if row else None
