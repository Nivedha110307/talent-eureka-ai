"""Initial candidate profile, jobs, saved jobs, and resume records."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("candidate_profiles", sa.Column("id",sa.String(64),primary_key=True),sa.Column("skills",sa.JSON(),nullable=False),sa.Column("projects",sa.JSON(),nullable=False),sa.Column("experience",sa.JSON(),nullable=False),sa.Column("education",sa.JSON(),nullable=False),sa.Column("preferred_roles",sa.JSON(),nullable=False),sa.Column("preferred_locations",sa.JSON(),nullable=False),sa.Column("experience_level",sa.String(80),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("jobs",sa.Column("id",sa.String(64),primary_key=True),sa.Column("title",sa.String(240),nullable=False),sa.Column("company",sa.String(240),nullable=False),sa.Column("location",sa.String(240),nullable=False),sa.Column("work_mode",sa.String(40),nullable=False),sa.Column("experience_level",sa.String(80),nullable=False),sa.Column("source",sa.String(160),nullable=False),sa.Column("source_type",sa.String(30),nullable=False),sa.Column("source_id",sa.String(240)),sa.Column("canonical_url",sa.String(1200),unique=True),sa.Column("description",sa.Text(),nullable=False),sa.Column("required_skills",sa.JSON(),nullable=False),sa.Column("preferred_skills",sa.JSON(),nullable=False),sa.Column("posted_at",sa.DateTime(timezone=True)),sa.Column("ingested_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("verified_at",sa.DateTime(timezone=True)),sa.Column("verification_status",sa.String(30),nullable=False),sa.Column("url",sa.String(1200),nullable=False,unique=True),sa.Column("active",sa.Boolean(),nullable=False))
    op.create_index("ix_jobs_title","jobs",["title"]); op.create_index("ix_jobs_company","jobs",["company"]); op.create_index("ix_jobs_work_mode","jobs",["work_mode"]); op.create_index("ix_jobs_source_type","jobs",["source_type"]); op.create_index("ix_jobs_active","jobs",["active"]); op.create_index("ix_jobs_location_mode","jobs",["location","work_mode"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE INDEX ix_jobs_search_vector ON jobs USING GIN (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(company,'')))")
    op.create_table("saved_jobs",sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),sa.Column("candidate_id",sa.String(64),sa.ForeignKey("candidate_profiles.id",ondelete="CASCADE"),nullable=False),sa.Column("job_id",sa.String(64),sa.ForeignKey("jobs.id",ondelete="CASCADE"),nullable=False),sa.Column("status",sa.String(30),nullable=False),sa.Column("notes",sa.Text(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("applied_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("candidate_id","job_id",name="uq_saved_candidate_job"))
    op.create_table("resume_records",sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),sa.Column("candidate_id",sa.String(64),sa.ForeignKey("candidate_profiles.id",ondelete="CASCADE"),nullable=False),sa.Column("filename",sa.String(255),nullable=False),sa.Column("content_type",sa.String(100),nullable=False),sa.Column("text",sa.Text(),nullable=False),sa.Column("page_count",sa.Integer(),nullable=False),sa.Column("uploaded_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("resume_records"); op.drop_table("saved_jobs")
    if op.get_bind().dialect.name == "postgresql": op.drop_index("ix_jobs_search_vector",table_name="jobs")
    for name in ("ix_jobs_location_mode","ix_jobs_active","ix_jobs_source_type","ix_jobs_work_mode","ix_jobs_company","ix_jobs_title"): op.drop_index(name,table_name="jobs")
    op.drop_table("jobs"); op.drop_table("candidate_profiles")
