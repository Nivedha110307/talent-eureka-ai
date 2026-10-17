from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CandidateProfile, Job

SAMPLE_JOBS = [
 {"id":"sample-001","title":"Backend Engineer","company":"Northstar Labs","location":"Bengaluru, India","work_mode":"Hybrid","experience_level":"Early career","source":"Synthetic demo","source_type":"synthetic","description":"Build reliable Python APIs and data services with FastAPI and PostgreSQL. Collaborate with product and platform teams.","required_skills":["Python","FastAPI","SQL"],"preferred_skills":["PostgreSQL","Docker"],"url":"https://example.com/jobs/backend-engineer"},
 {"id":"sample-002","title":"Data Analyst","company":"Fieldnote","location":"Remote (India)","work_mode":"Remote","experience_level":"Early career","source":"Synthetic demo","source_type":"synthetic","description":"Use SQL and Python to explore product data, build clear dashboards and explain trends to cross-functional teams.","required_skills":["SQL","Data analysis"],"preferred_skills":["Python","Tableau"],"url":"https://example.com/jobs/data-analyst"},
 {"id":"sample-003","title":"Analytics Engineer","company":"Juniper Works","location":"Pune, India","work_mode":"Hybrid","experience_level":"Early career","source":"Synthetic demo","source_type":"synthetic","description":"Transform warehouse data with SQL and Python. Design dependable models and partner with analysts on data quality.","required_skills":["SQL","Data modeling"],"preferred_skills":["Python","dbt"],"url":"https://example.com/jobs/analytics-engineer"},
 {"id":"sample-004","title":"Junior Platform Developer","company":"Open Current","location":"Remote","work_mode":"Remote","experience_level":"Entry level","source":"Synthetic demo","description":"Support internal developer tools and cloud-native services. Python scripting and Docker familiarity are useful.","required_skills":["Python","Linux"],"preferred_skills":["Docker","PostgreSQL"],"url":"https://example.com/jobs/platform-developer"},
]

def seed_database(db: Session) -> None:
    if db.scalar(select(CandidateProfile).where(CandidateProfile.id == "local-candidate")) is None:
        db.add(CandidateProfile(id="local-candidate"))
    for data in SAMPLE_JOBS:
        if db.get(Job, data["id"]) is None:
            db.add(Job(**data, canonical_url=data["url"], verification_status="synthetic"))
    db.commit()
