from __future__ import annotations

import csv
import io
import os
import re
from contextlib import asynccontextmanager
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, get_db
from .matching import match_job, normalize
from .models import Base, CandidateProfile, Job, ResumeRecord, SavedJob
from .resume_parser import parse_resume_text
from .seed import seed_database

@asynccontextmanager
async def lifespan(application):
    if os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true": Base.metadata.create_all(engine)
    with SessionLocal() as db: seed_database(db)
    yield

app = FastAPI(title="TalentEureka AI", version="0.2.0", lifespan=lifespan, description="Candidate-first career discovery API. Sample listings are synthetic demonstrations.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ProfileIn(BaseModel):
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    experience_level: str = ""

class ApplicationIn(BaseModel):
    status: str = "Saved"
    notes: str = ""

class IngestJob(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    company: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1)
    source: str = Field(min_length=1, max_length=160)
    url: HttpUrl
    location: str = "Location not provided"
    work_mode: str = "Unspecified"
    experience_level: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    source_id: str | None = None
    source_type: str = "imported"
    verification_status: str = "unverified"

def profile_data(profile: CandidateProfile) -> dict:
    return {key: getattr(profile, key) for key in ("skills", "projects", "experience", "education", "preferred_roles", "preferred_locations", "experience_level")}

def job_data(job: Job, profile: dict, saved: bool) -> dict:
    return {"id":job.id,"title":job.title,"company":job.company,"location":job.location,"work_mode":job.work_mode,"experience_level":job.experience_level,"source":job.source,"source_type":job.source_type,"description":job.description,"required_skills":job.required_skills,"preferred_skills":job.preferred_skills,"posted_at":job.posted_at,"verified_at":job.verified_at,"verification_status":job.verification_status,"url":job.url,"match":match_job(profile, {"title":job.title,"experience_level":job.experience_level,"description":job.description,"required_skills":job.required_skills,"preferred_skills":job.preferred_skills}),"saved":saved}

@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
        return {"status":"ok", "database":"connected", "database_url_scheme":engine.dialect.name}
    except Exception as exc:
        raise HTTPException(503, "Database unavailable") from exc

@app.get("/api/profile")
def get_profile(db: Session = Depends(get_db)):
    profile = db.get(CandidateProfile, "local-candidate")
    if profile is None: raise HTTPException(404, "Candidate profile not initialized")
    return profile_data(profile)

@app.put("/api/profile")
def save_profile(data: ProfileIn, db: Session = Depends(get_db)):
    profile = db.get(CandidateProfile, "local-candidate")
    if profile is None:
        profile = CandidateProfile(id="local-candidate"); db.add(profile)
    for key, value in data.model_dump().items(): setattr(profile, key, value)
    db.commit(); db.refresh(profile)
    return profile_data(profile)

@app.get("/api/jobs")
def list_jobs(q: str = "", location: str = "", remote: str = "", source: str = "", limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    if limit < 1 or limit > 100 or offset < 0: raise HTTPException(422, "limit must be 1–100 and offset cannot be negative")
    stmt = select(Job).where(Job.active.is_(True))
    if q:
        if engine.dialect.name == "postgresql":
            vector = func.to_tsvector("english", func.coalesce(Job.title, "") + " " + func.coalesce(Job.description, "") + " " + func.coalesce(Job.company, ""))
            query = func.plainto_tsquery("english", q)
            stmt = stmt.where(vector.op("@@")(query)).order_by(func.ts_rank_cd(vector, query).desc())
        else:
            terms = [term for term in re.findall(r"[\w+#.]+", q.lower()) if term]
            if terms:
                clauses = [or_(Job.title.ilike(f"%{t}%"), Job.description.ilike(f"%{t}%"), Job.company.ilike(f"%{t}%")) for t in terms]
                stmt = stmt.where(or_(*clauses))
    if location: stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if remote: stmt = stmt.where(Job.work_mode.ilike(remote))
    if source: stmt = stmt.where(Job.source_type == source)
    db_jobs = db.scalars(stmt.order_by(Job.id)).all()
    profile = db.get(CandidateProfile, "local-candidate") or CandidateProfile(id="local-candidate")
    saved_ids = set(db.scalars(select(SavedJob.job_id).where(SavedJob.candidate_id == "local-candidate")).all())
    results = [job_data(job, profile_data(profile), job.id in saved_ids) for job in db_jobs]
    lexical_order={job.id:index for index,job in enumerate(db_jobs)}
    results.sort(key=lambda row: (-row["match"]["score"], lexical_order.get(row["id"],0)))
    return {"items":results[offset:offset+limit], "total":len(results), "offset":offset, "limit":limit, "synthetic_data":all(j.source_type == "synthetic" for j in db_jobs)}

@app.put("/api/jobs/{job_id}/saved")
def toggle_saved(job_id: str, db: Session = Depends(get_db)):
    if db.get(Job, job_id) is None: raise HTTPException(404, "Job not found")
    saved = db.scalar(select(SavedJob).where(SavedJob.candidate_id == "local-candidate", SavedJob.job_id == job_id))
    if saved:
        db.delete(saved); db.commit(); return {"saved":False}
    db.add(SavedJob(candidate_id="local-candidate", job_id=job_id)); db.commit()
    return {"saved":True}

@app.get("/api/applications")
def applications(db: Session = Depends(get_db)):
    rows = db.scalars(select(SavedJob).where(SavedJob.candidate_id == "local-candidate").order_by(SavedJob.created_at.desc())).all()
    return {"items":[{"job":{**job_data(row.job, profile_data(row.candidate), True), "match":None}, "status":row.status, "notes":row.notes} for row in rows]}

@app.patch("/api/applications/{job_id}")
def update_application(job_id: str, data: ApplicationIn, db: Session = Depends(get_db)):
    allowed = {"Interested", "Saved", "Applied", "Interviewing", "Offered", "Rejected", "Withdrawn"}
    if data.status not in allowed: raise HTTPException(422, "Unsupported application status")
    row = db.scalar(select(SavedJob).where(SavedJob.candidate_id == "local-candidate", SavedJob.job_id == job_id))
    if not row: raise HTTPException(404, "Saved job not found")
    row.status = data.status; row.notes = data.notes
    row.applied_at = datetime.now(timezone.utc) if data.status == "Applied" else row.applied_at
    db.commit(); return {"status":row.status,"notes":row.notes}

@app.post("/api/resume/parse")
async def parse_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type != "application/pdf" or not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Upload a PDF file")
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024: raise HTTPException(413, "PDF must be 5 MB or smaller")
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise HTTPException(422, "Could not read this PDF. Try a text-based PDF or create a profile manually.") from exc
    if not text.strip(): raise HTTPException(422, "No selectable text found. This may be a scanned PDF; create a profile manually for now.")
    profile = db.get(CandidateProfile, "local-candidate")
    if profile is None: profile = CandidateProfile(id="local-candidate"); db.add(profile)
    resume = ResumeRecord(candidate_id=profile.id, filename=os.path.basename(file.filename), content_type=file.content_type, text=text[:30000], page_count=len(reader.pages))
    db.add(resume); db.commit()
    parsed = parse_resume_text(text[:30000])
    return {"text":text[:30000], **parsed, "review_required":True, "message":"Suggested details are unconfirmed. Review the excerpts and choose what to add to your profile."}

@app.delete("/api/profile/resume")
def delete_resume(db: Session = Depends(get_db)):
    db.query(ResumeRecord).filter(ResumeRecord.candidate_id == "local-candidate").delete(synchronize_session=False)
    db.commit(); return {"deleted":True}

@app.delete("/api/profile")
def delete_profile(db: Session = Depends(get_db)):
    profile=db.get(CandidateProfile,"local-candidate")
    if profile: db.delete(profile); db.commit()
    return {"deleted":True}

def canonicalize_url(url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit
    parts=urlsplit(url.strip())
    host=(parts.hostname or "").lower()
    if parts.port: host=f"{host}:{parts.port}"
    path=parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https",host,path,"", ""))

def description_similarity(left: str, right: str) -> float:
    a={word for word in normalize(left).split() if len(word)>2}; b={word for word in normalize(right).split() if len(word)>2}
    return len(a & b)/max(1,len(a | b))

@app.post("/api/ingest/{format}")
async def ingest_jobs(format: str, payload: dict, db: Session = Depends(get_db)):
    if format == "csv":
        rows = list(csv.DictReader(io.StringIO(payload.get("csv", ""))))
        for row in rows:
            for field in ("required_skills", "preferred_skills"):
                row[field] = [x.strip() for x in row.get(field, "").split("|") if x.strip()]
        records = rows
    elif format == "json": records = payload.get("jobs")
    else: raise HTTPException(400, "Supported formats: json and csv")
    if not isinstance(records, list): raise HTTPException(400, "Provide {jobs: [...]} or {csv: '...'}")
    added = 0
    skipped_invalid = 0
    potential_duplicates=[]
    for raw in records:
        if not isinstance(raw, dict): skipped_invalid+=1; continue
        try:
            row=IngestJob.model_validate(raw).model_dump()
            row["url"]=str(row["url"])
        except ValidationError:
            skipped_invalid+=1; continue
        url = row["url"].strip()
        canonical=canonicalize_url(url)
        if not url or db.scalar(select(Job.id).where(or_(Job.url == url, Job.canonical_url == canonical))): continue
        potential=[]
        for existing in db.scalars(select(Job)).all():
            same_company=normalize(existing.company)==normalize(row["company"])
            same_title=normalize(existing.title)==normalize(row["title"])
            similarity=description_similarity(existing.description,row["description"])
            if same_company and same_title and similarity >= 0.45:
                potential.append({"job_id":existing.id,"title":existing.title,"company":existing.company,"description_similarity":round(similarity,3)})
        item = {"id":str(uuid.uuid4()), "location":"Location not provided", "work_mode":"Unspecified", "experience_level":"", "required_skills":[], "preferred_skills":[], "source_type":"imported", "verification_status":"unverified", **row, "canonical_url":canonical}
        db.add(Job(**item)); added += 1
        if potential: potential_duplicates.append({"incoming_url":url,"candidates":potential})
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "A duplicate canonical URL already exists")
    return {"added":added,"skipped_invalid":skipped_invalid,"total":len(db.scalars(select(Job.id)).all()),"potential_duplicates":potential_duplicates}
