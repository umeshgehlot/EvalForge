# EvalForge — LLM Evaluation & Observability Platform

EvalForge is a full-stack dashboard for evaluating and inspecting LLM application outputs. It includes dataset management, app endpoint registration, configurable scorers, asynchronous evaluation runs, result comparison, benchmark history, and trace details. The bundled demo application is a small retrieval-augmented question-answering service.

> **Implementation notes:** This README describes behavior in the current checkout, not a production-ready deployment. Authentication routes exist, but product API routes are not protected by authentication. App-version model and prompt fields are stored as metadata; the worker currently uses the registered endpoint URL and sends a fixed `top_k=5` request. Evaluation rows are processed sequentially inside a Celery task.

## Architecture

```text
Browser (Next.js) ──HTTP──> FastAPI backend ──> PostgreSQL / pgvector
                                  │                       ▲
                                  └── enqueue ─> Redis ─> Celery worker
                                                        │
                                                        └── POST /ask ─> RAG demo app
                                                                          │
                                                                          └── pgvector
```

- **Backend:** FastAPI, async SQLAlchemy, Alembic migrations, and PostgreSQL.
- **Worker:** Celery with Redis as the broker; one task processes a run's dataset rows sequentially.
- **Demo app:** FastAPI, LlamaIndex, PostgreSQL/pgvector, and OpenTelemetry spans returned with each answer.
- **Frontend:** Next.js 14, TypeScript, Tailwind, and dashboard pages for datasets, versions, scorers, runs, comparison, and benchmark history.
- **Scorers:** exact match, keyword coverage, JSON validity, LLM correctness judge, and custom claim-based faithfulness scoring.

The faithfulness scorer is project code; it is not the official RAGAS package. The benchmark endpoint calculates regression indicators when benchmark history is requested; runs are not automatically compared and flagged on completion.

## Requirements

- Docker Desktop or Docker Engine with the Compose plugin
- An OpenAI API key for the bundled judge and demo RAG app
- Node package lockfile for the frontend image build: **the current checkout does not include one, but its Dockerfile runs `npm ci`.** Generate and commit a compatible lockfile before building the complete Compose stack.

## Start the services

The Compose environment file is [infra/.env.example](infra/.env.example). From PowerShell:

```powershell
Set-Location infra
Copy-Item .env.example .env
```

Edit `infra/.env`: set `OPENAI_API_KEY` and replace the default `SECRET` with a long random value. Then start the stack:

```powershell
docker compose up --build -d
```

The backend container runs `alembic upgrade head` at startup. The exposed services are:

- Dashboard: <http://localhost:3000>
- Backend API and Swagger UI: <http://localhost:8001/docs>
- Demo RAG API: <http://localhost:8002/docs>

PostgreSQL and Redis use the Compose defaults in the sample file. Change those values before running if the defaults are unsuitable for your machine.

## Load sample data and demo documents

The seed script inserts example datasets, app versions, and precomputed runs. It does not make live calls to the demo app:

```powershell
docker compose exec backend python seed.py
```

The demo app's documents must be embedded separately before retrieval returns useful context:

```powershell
docker compose exec demo-app python ingest.py
```

The demo database is created by `infra/init-db.sql` when PostgreSQL initializes a new volume. If Postgres already has an existing volume, initialization scripts are not rerun automatically.

## Typical workflow

1. Open the dashboard and create or inspect a dataset. Dataset rows can be uploaded as CSV.
2. Register an app version pointing to the demo endpoint, normally `http://demo-app:8000` from inside the Compose network.
3. Select the dataset, app version, and scorer IDs to create a run.
4. Poll run status and inspect results, scorer reasoning, retrieved chunks, or recorded spans.
5. Compare two runs or open benchmark history to calculate differences and display pass-rate trends.

The worker currently reads the endpoint URL and scorer records when it runs. It does not apply the saved prompt/model/retriever configuration fields to the demo app, and scorer settings are not snapshotted per run.

## API overview

FastAPI's interactive API reference is at `/docs`. Main route groups include:

| Route group | Example operations |
|---|---|
| `/health` | Service health |
| `/datasets` | Dataset CRUD, CSV row upload, row listing and deletion |
| `/app-versions` | Register, list, inspect, and delete endpoint configurations |
| `/scorers` | List, create, test, and delete scorers |
| `/runs` | Create/list/inspect/delete runs; poll status, metrics, results and traces |
| `/runs/compare` | Compare two runs, including changed items and metric deltas |
| `/runs/benchmark` | Return completed-run history and calculated regression indicators for a dataset |
| `/auth` and `/users` | Authentication and user-management routes |

Authentication endpoints are present, but the dataset, scorer, version, and run routes currently do not enforce authenticated-user dependencies. Do not expose this configuration as a secured multi-user service without adding authorization.

## Development and tests

Backend tests use pytest. Install backend dependencies and the test requirements in the backend environment, then run from `backend/`:

```bash
python -m pip install -r requirements-test.txt
pytest
```

The requirements-test file includes runtime requirements. Frontend development commands are `npm install`, `npm run dev`, `npm run build`, and `npm start` from `frontend/` (a package lockfile is needed for `npm ci` and the current Docker build).

## Project layout

```text
backend/    FastAPI API, SQLAlchemy models, migrations, and scorers
worker/     Celery application and evaluation task
demo-app/   RAG endpoint, tracing, and document-ingestion script
frontend/   Next.js dashboard
infra/      Compose definition, Postgres initialization, and Compose env template
DOCS.md     Extended technical notes (some design descriptions may be aspirational)
```

## Limitations

- No production authentication/authorization or tenant isolation on product routes.
- The worker processes rows sequentially; there is no per-row task fan-out.
- Saved app-version settings do not currently configure the called application beyond its endpoint URL.
- Demo documents require manual ingestion; seeding example runs does not ingest them.
- The frontend Docker build currently needs a package lockfile to satisfy `npm ci`.
- Compose health checks cover PostgreSQL and Redis, not the backend or demo app.
