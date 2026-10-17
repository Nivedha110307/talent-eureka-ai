# TalentEureka AI

Candidate-first career discovery prototype. The included job listings are labeled synthetic demonstrations, not live vacancies. They use `example.com` URLs, and no external job source is configured.

## Implemented

- React + TypeScript + Vite candidate interface: discovery, role exploration, saved opportunities, and profile editor.
- FastAPI service with SQLAlchemy 2.x database sessions. SQLite is the zero-setup local default; PostgreSQL can be selected through `DATABASE_URL`.
- Alembic initial migration for candidate profiles, jobs, saved/application records, and resume metadata/text. Local development can initialize SQLite automatically; Compose applies the migration before starting the API.
- Synthetic seed listings, profile editing, search/filtering, save/unsave, application status/notes API, and JSON/CSV ingestion.
- Deterministic match score: `100 × (0.60·required + 0.20·preferred + 0.10·role title overlap + 0.10·experience context)`. Partial requirement evidence contributes half credit. Scores describe relevance, not hiring odds.
- Resume PDF upload in the profile editor (5 MB limit), text extraction, selectable skill suggestions with evidence excerpts, section suggestions, and human review before saving. Scanned PDFs are rejected with guidance. Extraction is heuristic and needs review.
- Duplicate canonical URL detection and potential duplicate warnings based on normalized company/title plus description overlap. Potential duplicates are reported and are not silently merged.
- PostgreSQL full-text lexical retrieval with a GIN expression index; SQLite development uses a substring-search fallback.
- Five synthetic evaluation queries report Precision@3, Recall@3, MRR, and nDCG@3 for lexical, token-overlap fallback, and RRF. The fallback is not an embedding model.

## Local setup

Requires Python 3.11+ and Node 20+. In PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --app-dir backend
```

In another terminal:

```powershell
npm install
npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs. The default database is `sqlite:///./talenteureka.db`; profile and save changes persist across API restarts.

## PostgreSQL with Docker Compose

Create a local, untracked environment file from the example and set a URL-safe local development password:

```powershell
Copy-Item .env.example .env
```

Then run:

```powershell
docker compose up --build
```

Compose starts PostgreSQL 16 with pgvector, applies Alembic migrations, seeds sample listings, and starts the API and frontend. Docker was not available in the development environment used for this implementation, so this path still needs a local Compose run.

## Resume and privacy

Resume text and extracted metadata are stored in the configured database. The profile review UI lets users edit profile fields and choose suggested skills; resume text extraction suggestions do not automatically add skills. `DELETE /api/profile/resume` deletes stored resume records, and `DELETE /api/profile` deletes the local demo profile and related rows.

This prototype has **no authentication or user-level authorization**. It uses a single `local-candidate` profile shared by all local visitors. Do not expose it to a network or upload sensitive personal resumes until authentication, per-user isolation, secure storage, and retention controls are implemented.

## Tests

```powershell
python -m pytest -q
```

The current suite has 12 tests for evidence matching (exact, synonym, partial, missing, empty/incomplete, ambiguous), API profile/search/save behavior, persistence across database sessions, and exact/potential duplicate ingestion. The suite passed in the available SQLite environment. PostgreSQL-specific integration and visual end-to-end browser tests have not run.

## Retrieval evaluation

```powershell
python scripts/evaluate.py
```

Writes `reports/retrieval-evaluation.json` and `.md` from the checked-in synthetic judgments. Reported scores are measured on this small toy set only. Semantic mode remains an explicitly named lexical-overlap fallback; locally runnable sentence embeddings and pgvector retrieval are not implemented yet.

## Database benchmark

```powershell
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@localhost:5432/talenteureka"
python scripts/benchmark_postgres.py
```

The benchmark requires a populated `jobs` table and runs seven `EXPLAIN (ANALYZE, BUFFERS)` executions. No PostgreSQL performance result is claimed because Docker/PostgreSQL was unavailable here.

## Frontend build status and limits

The repository did not have a lockfile or installed dependencies. `npm install` completed with the declared package ranges unchanged and created `package-lock.json`; `npm run build` passed (TypeScript compilation and Vite production bundle). The build needed permission to spawn esbuild on this Windows environment. An HTTP integration smoke check confirmed the Vite page and transformed React module were served, the module used the configured API URL, and the API returned a matching job with the expected CORS header. The in-app browser itself timed out while attaching, so visual browser inspection was not completed.

Authentication, multi-user data isolation, pgvector embeddings and hybrid ranking in the live search endpoint, comprehensive ingestion validation, PostgreSQL integration tests, stale-listing verification workflows, and actual Compose verification remain unfinished.
