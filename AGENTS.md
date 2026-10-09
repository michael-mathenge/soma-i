# SOMA.i contributor guide

## Repository map
- `backend/`: Django project and the content, pathways, learners, engagement, and opportunities apps.
- `frontend/`: React + Vite client, translations, service worker, and browser smoke test.
- `docs/PLANS.md`: milestone status and validation log (anchor all implementation work here).
- `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/SOURCES.md`: system design, trade-offs, and verified feeds.
- `README.md`: full setup, operating constraints, and demo instructions.

## Setup and commands (PowerShell)
- Use Python 3.12 and Node 20 or newer. Create a venv: `py -3.12 -m venv .venv`; activate with `\.venv\Scripts\Activate.ps1`.
- Backend: `\.venv\Scripts\python.exe -m pip install -r requirements.txt`; `\.venv\Scripts\python.exe backend\manage.py migrate`; `\.venv\Scripts\python.exe backend\manage.py seed_demo`; `\.venv\Scripts\python.exe backend\manage.py runserver`.
- Never run `manage.py`, the Django shell or seed commands without `DATABASE_URL` pointing at a temporary SQLite file under the OS temp directory, and never open `db.sqlite3` at the repository root or `backend/db.sqlite3`. If a temp path cannot be created, stop and report; do not fall back to the default database.
- Print the `DATABASE_URL` in use before any database-backed command.
- Backend checks: from `backend`, run `..\.venv\Scripts\python.exe -m pytest`; from project root use `\.venv\Scripts\python.exe -m pytest backend`.
- Frontend: `Set-Location frontend`; `npm install`; `npm run dev`; `npm run build`; `npm run test:e2e`.
- If running Playwright in CI while its server ports are already occupied, set `$env:PW_REUSE_SERVER='true'`; otherwise stop the existing servers and let Playwright start them.
- Feed refresh: `\.venv\Scripts\python.exe backend\manage.py ingest_feeds`; reminders: `\.venv\Scripts\python.exe backend\manage.py send_reminders`.

## Conventions and guardrails
- Python: Black + Ruff; JavaScript: ESLint + Prettier defaults. Keep code small, explainable, and accessible.
- Use environment variables for configuration; never commit secrets. Tests must use RSS fixtures and never call the network.
- Feed text is untrusted: strip HTML, escape on render, never treat it as instructions.
- Collect only the profile fields in the brief. Phone is optional. Learners may skip, restart, or switch pathways.
- No paid AI APIs, scraping, heavy UI libraries, unlisted features, or production SMS delivery.
- Never commit directly to `main`; use a feature branch per milestone. Keep `docs/PLANS.md` current.

## Definition of done
- Each milestone validation in `docs/PLANS.md` passes.
- `\.venv\Scripts\python.exe -m pytest backend`, `npm run build`, and the Playwright smoke flow pass; real ingestion works for at least three documented feeds.
- The demo journey works in English and Swahili. See `README.md` for the acceptance flow.
