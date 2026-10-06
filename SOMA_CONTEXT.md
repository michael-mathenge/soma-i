# SOMA.i Context Brief

## 1. Purpose and target learner

SOMA.i is a Kenya-oriented learning proof of concept that connects curated learning content to practical skills, checkpoints, and next-step opportunities. Its target learner is someone pursuing entry-level data analysis, web development, or digital marketing skills. Learner age, education level, and prior-experience requirements are **unknown**.

## 2. Tech stack and how to run it

- Backend: Python 3.12, Django, Django REST Framework, and SQLite by default; PostgreSQL can be configured through `DATABASE_URL`.
- Frontend: Node 20 or newer, React 19, React Router, Axios, and Vite 6. Playwright provides the browser smoke flow.
- The frontend package scripts, as declared in `frontend/package.json`, are:
  - `npm run dev` — start the Vite development server.
  - `npm run build` — build the frontend and report compressed bundle size.
  - `npm run preview` — serve the production build locally.
  - `npm run test:e2e` — run Playwright tests.
  - `npm run lint` — lint frontend source and tests.
  - `npm run format` — format frontend source, tests, and top-level frontend files.

README setup and local run commands (PowerShell, from the repository root unless stated):

```powershell
py -3.12 -m venv .venv
\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python backend\manage.py migrate
python backend\manage.py seed_demo
```

In a first PowerShell window:

```powershell
Set-Location frontend
npm install
npx playwright install chromium
npm run dev
```

In a second PowerShell window:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe manage.py runserver
```

Environment variable names present in `.env.example` (values intentionally omitted): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `AFRICASTALKING_USERNAME`, `AFRICASTALKING_API_KEY`, and `SOMA_SENDER`.

## 3. Folder map

- `backend/soma/`: Django settings, URL configuration, and WSGI entry point.
- `backend/content/`: source and item models, RSS feed definitions, ingestion, skill keyword tagging, management command, and fixture-based tests.
- `backend/pathways/`: pathways, skills/checkpoints, progression and recommendations, demo seeding, and progress tests.
- `backend/learners/`: learner profile and session-based API endpoints for onboarding, settings, progress, checkpoints, and opportunities.
- `backend/engagement/`: reminder records, message templates, sender classes, and the due-reminder command.
- `backend/opportunities/`: opportunity model and skill-match ranking with tests; demo records are sample listings.
- `frontend/src/`: React application, API client, styling, and English/Swahili translations.
- `frontend/public/`: web manifest and service worker for app-shell and recent-read caching.
- `frontend/tests/`: Playwright bilingual demo journey.
- `frontend/scripts/`: compressed bundle-size reporting used by the build script.
- `docs/`: milestone log (`PLANS.md`), architecture, decisions, and verified RSS sources.
- `README.md`, `AGENTS.md`: setup/demo guidance and contributor constraints.

## 4. Features: built / partly built / not started

Statuses below combine the milestone report in `docs/PLANS.md` with the current implementation and explicitly documented later work.

**Built**

- Three seeded pathways: Data Analyst, Web Developer, and Digital Marketing Assistant.
- Anonymous, session-linked learner profiles; onboarding, pathway switch/restart/skip, item completion, and checkpoint progress.
- Rule-based skill tagging and recommendations, with low-data items preferred within matching skills.
- Three-question, self-attested checkpoints and next-step responses with sample skill-matched opportunities.
- English and Swahili interface and reminder message templates.
- Offline app-shell and cached dashboard/items reads; progress writes require connectivity.
- RSS ingestion with source/date traceability and deduplication.

**Partly built**

- Weekly reminders: due selection, message generation, logging, and console output are implemented. The Africa’s Talking sender is only a sandbox integration stub and does not deliver SMS.
- Offline support covers the shell and selected reads; progress submissions do not work offline.

**Not started / documented as later work**

- Production SMS provider delivery and durable user accounts.
- Broader curated feeds and live opportunity aggregation.
- Cross-device synchronization and deployment hardening.

## 5. Data sources and fetching

The documented external content sources are RSS feeds:

- MIT News Research — `https://news.mit.edu/rss/research`
- freeCodeCamp News — `https://www.freecodecamp.org/news/rss/`
- MDN Blog — `https://developer.mozilla.org/en-US/blog/rss.xml`

`python backend\manage.py ingest_feeds` runs the `content` management command. It parses each configured feed, creates deduplicated items by URL, cleans summaries, records source and publication date, and tags new items using case-insensitive keyword rules. A fetch or parse error is reported for that source while processing continues for the remaining feeds. The docs report successful live ingestion on 2026-10-02; tests are documented as using local RSS fixtures rather than network access.

The application also exposes its own Django REST API under `/api/`, including health, pathways, learner profile, dashboard, items, checkpoints, pathway actions, and opportunities. These are internal application endpoints, not third-party APIs. No live external opportunity API is documented or implemented; seeded opportunities are labelled samples.

## 6. How reminders/checkpoints work today

**Reminders:** A learner can opt in through Settings. `python backend\manage.py send_reminders` selects opted-in learners with a chosen pathway, skips learners with a reminder logged in the last seven days, and skips learners without a next checkpoint. It builds a message in the learner’s preferred language, truncates messages above 160 characters, sends via the configured sender, and records a `ReminderLog`. Console output is the working sender. Selecting `SOMA_SENDER=africastalking` uses a stub: it checks for an API key but does not make a network request or deliver a message. Weekly is the default frequency; no other scheduling frequency is implemented in the command.

**Checkpoints:** Each ordered pathway skill has a checkpoint. The learner can complete it after self-attesting and submitting answers to all three configured questions, or skip it. Completion records the status and answers and returns unlocked-skill information, the next checkpoint, recommended items, and matched sample opportunities. A skipped checkpoint is omitted from the next-checkpoint selection. Demo data seeds Amina Demo partway through the Data Analyst pathway.

## 7. Known bugs, TODOs, and rough edges

- The `/next` page fallback builds its data from the dashboard and sets `opportunities: []`; navigating directly to `/next` without the checkpoint-completion response can therefore show no opportunities. File: `frontend/src/App.jsx`.
- Africa’s Talking integration is not delivery-ready: `send()` only prints a stub notice after checking for a configured API key. File: `backend/engagement/senders.py`.
- `docs/ARCHITECTURE.md` says a reminder log records a destination when provided, but the current `ReminderLog` model has no destination field and the command does not pass a destination. Files: `docs/ARCHITECTURE.md`, `backend/engagement/models.py`, `backend/engagement/management/commands/send_reminders.py`.
- The weekly due check uses the most recent reminder log timestamp as its seven-day gate; actual scheduled execution is outside the repository’s documented command flow. Scheduling/deployment details are **unknown**. File: `backend/engagement/management/commands/send_reminders.py`.
- The source has no `TODO` or `FIXME` markers in the scanned application/docs files. This is a text search result, not a guarantee that no other defects exist.

## 8. Open questions for the project owner

- Who is the intended learner beyond the entry-level Kenya-oriented pathways (for example, age, education, location, and prior experience)? These details are **unknown**.
- Should reminders remain a local console demo, or is real SMS delivery in scope? If SMS is in scope, which provider and what consent/destination requirements should apply?
- Which sources should supply real opportunities, and how should stale or expired listings be handled?
- What deployment environment, account model, and cross-device persistence are intended, if any?
- Should checkpoint quiz answers be scored or used to gate completion? The current API validates that three answers are present but does not grade them.
