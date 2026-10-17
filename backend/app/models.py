from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default="local-candidate")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    experience: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    preferred_roles: Mapped[list] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[list] = mapped_column(JSON, default=list)
    experience_level: Mapped[str] = mapped_column(String(80), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resumes: Mapped[list["ResumeRecord"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    saved_jobs: Mapped[list["SavedJob"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(240), index=True)
    company: Mapped[str] = mapped_column(String(240), index=True)
    location: Mapped[str] = mapped_column(String(240), default="Location not provided")
    work_mode: Mapped[str] = mapped_column(String(40), default="Unspecified", index=True)
    experience_level: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(160))
    source_type: Mapped[str] = mapped_column(String(30), default="imported", index=True)
    source_id: Mapped[str | None] = mapped_column(String(240), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(1200), nullable=True, unique=True)
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified")
    url: Mapped[str] = mapped_column(String(1200), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    __table_args__ = (Index("ix_jobs_location_mode", "location", "work_mode"),)

class SavedJob(Base):
    __tablename__ = "saved_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), default="Saved")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate: Mapped[CandidateProfile] = relationship(back_populates="saved_jobs")
    job: Mapped[Job] = relationship()
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_saved_candidate_job"),)

class ResumeRecord(Base):
    __tablename__ = "resume_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    candidate: Mapped[CandidateProfile] = relationship(back_populates="resumes")
