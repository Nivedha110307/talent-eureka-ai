"""Run repeatable EXPLAIN (ANALYZE, BUFFERS) against a local PostgreSQL jobs table.

Requires DATABASE_URL and a jobs table with title, description, required_skills,
location columns. It intentionally refuses to invent a benchmark dataset/result.
"""
import os, statistics, time
from sqlalchemy import create_engine, text

url=os.getenv('DATABASE_URL')
if not url or not url.startswith(('postgresql://','postgresql+psycopg://')):
    raise SystemExit('Set DATABASE_URL to a PostgreSQL connection; no benchmark was run.')
engine=create_engine(url)
query=text("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT id FROM jobs WHERE lower(title) LIKE :term OR lower(description) LIKE :term ORDER BY id LIMIT 20")
with engine.connect() as conn:
    try: conn.execute(text('SELECT 1 FROM jobs LIMIT 1'))
    except Exception as exc: raise SystemExit(f'Expected a populated jobs table; no benchmark was run: {exc}')
    timings=[]; plans=[]
    for _ in range(7):
        start=time.perf_counter(); plan=conn.execute(query,{'term':'%python%'}).scalars().all(); timings.append((time.perf_counter()-start)*1000); plans.append('\n'.join(plan))
    print({'dataset_rows':conn.execute(text('SELECT count(*) FROM jobs')).scalar_one(),'postgres_version':conn.execute(text('SHOW server_version')).scalar_one(),'query':'title/description contains python, limit 20','repeats':len(timings),'median_client_ms':round(statistics.median(timings),3),'explain_analyze_buffers':plans[-1]})
