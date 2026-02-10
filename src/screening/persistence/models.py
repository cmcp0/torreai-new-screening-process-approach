from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import create_engine, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import DateTime

from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID


class Base(DeclarativeBase):
    pass


def _uuid_col(**kwargs: Any):
    return mapped_column(PG_UUID(as_uuid=True), **kwargs)


class CandidateModel(Base):
    __tablename__ = "candidates"
    id: Mapped[UUID] = _uuid_col(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(nullable=False)
    skills: Mapped[dict] = mapped_column(JSONB, nullable=False)
    jobs: Mapped[dict] = mapped_column(JSONB, nullable=False)


class JobOfferModel(Base):
    __tablename__ = "job_offers"
    id: Mapped[UUID] = _uuid_col(primary_key=True)
    external_id: Mapped[str] = mapped_column(nullable=False, index=True)
    objective: Mapped[str] = mapped_column(nullable=False)
    strengths: Mapped[dict] = mapped_column(JSONB, nullable=False)
    responsibilities: Mapped[dict] = mapped_column(JSONB, nullable=False)


class ApplicationModel(Base):
    __tablename__ = "applications"
    id: Mapped[UUID] = _uuid_col(primary_key=True)
    candidate_id: Mapped[UUID] = _uuid_col(nullable=False, index=True)
    job_offer_id: Mapped[UUID] = _uuid_col(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class CallModel(Base):
    __tablename__ = "calls"
    id: Mapped[UUID] = _uuid_col(primary_key=True)
    application_id: Mapped[UUID] = _uuid_col(nullable=False, index=True)
    status: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    transcript: Mapped[dict] = mapped_column(JSONB, nullable=False)


class AnalysisModel(Base):
    __tablename__ = "analyses"
    id: Mapped[UUID] = _uuid_col(primary_key=True)
    application_id: Mapped[UUID] = _uuid_col(nullable=False, unique=True, index=True)
    fit_score: Mapped[int] = mapped_column(nullable=False)
    skills: Mapped[dict] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="completed")


class EntityEmbeddingModel(Base):
    """Stores embeddings for candidates and job offers (FR-2.1, FR-2.2)."""
    __tablename__ = "entity_embeddings"
    id: Mapped[UUID] = _uuid_col(primary_key=True)
    entity_type: Mapped[str] = mapped_column(nullable=False, index=True)  # "candidate" | "job_offer"
    entity_id: Mapped[UUID] = _uuid_col(nullable=False, index=True)
    embedding: Mapped[dict] = mapped_column(JSONB, nullable=False)  # list[float] as JSON
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_entity_embeddings_entity"),)


class OutboxEventModel(Base):
    """Durable outbox for at-least-once event publishing."""

    __tablename__ = "outbox_events"
    id: Mapped[UUID] = _uuid_col(primary_key=True)
    event_type: Mapped[str] = mapped_column(nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True, index=True)
    last_error: Mapped[Optional[str]] = mapped_column(nullable=True)


def create_engine_from_url(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory(engine):
    return sessionmaker(engine, class_=Session, expire_on_commit=False)
