# SOMA.i — learning that leads somewhere

SOMA.i is an invention-sprint proof of concept that connects credible learning content to practical skills, checkpoints, and next-step opportunities. Its primary track is **Guidance, Pathways & Opportunity**; it also demonstrates **Access & Discovery** through curated RSS and **Engagement** through checkpoints and reminders.

## How the operating constraints are addressed

- **Credibility:** vetted RSS sources, visible publisher links, and source/date traceability; see `docs/SOURCES.md`.
- **Low bandwidth:** text-first screens, estimated reading times, low-data ranking, small assets, and offline read caching.
- **Accessibility:** semantic controls, labels, keyboard navigation, contrast, and plain language.
- **Personalisation without exclusion:** pathway skill matching guides recommendations, while skip, restart, and switch remain available.
- **Privacy:** minimal learner fields, optional phone, and delete-my-data endpoint.
- **Multilingual:** English and Swahili UI and reminder templates.
- **Local relevance:** Kenya-oriented pathways and clearly labelled sample local opportunities.

## Setup (PowerShell)

Install Python 3.12 and Node 20 or newer, then from the repository root:

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

In another window, start Django:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe manage.py runserver
```

Open the Vite URL printed by the frontend command. For automated checks:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest
Set-Location ..\frontend
npm run build
npm run test:e2e
```

If running Playwright in CI while its server ports are already occupied, set `$env:PW_REUSE_SERVER='true'` before `npm run test:e2e`. Without this flag, Playwright starts its own backend and preview servers.

To ingest live feeds or preview due reminders, run `python backend\manage.py ingest_feeds` or `python backend\manage.py send_reminders` from the repository root. Tests use local XML fixtures and do not require network access. Set `DATABASE_URL` to a PostgreSQL URL and configure the matching driver for a later database switch. Never place real credentials in `.env.example`.

## Demo script

1. Open SOMA.i, select English or Kiswahili, and choose a pathway.
2. Open the Data Analyst pathway, inspect remaining skills, and open a recommended lesson.
3. Mark a lesson done, complete the three-question checkpoint, and inspect the unlocked skill, next checkpoint, and Kenya sample opportunities.
4. Switch the language in Settings, confirm the same flow copy is localized, and opt into weekly reminders if desired.
5. Reload with the network disabled to show cached app shell and last-viewed pathway/items; progress submissions need connectivity.

The demo learner is `Amina Demo`, mid-way through Data Analyst, with seeded content and sample opportunities. `docs/PLANS.md` tracks milestone status and validation; `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/SOURCES.md` record design details.
