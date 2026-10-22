# SOMA.i — learning that leads somewhere

SOMA.i connects curated RSS learning content to goal-based pathways, checkpoints, reminders and sample opportunities. It is a proof of concept for the Andela x OpenAI x MIVA Codex Accelerator theme, “Learning That Stays With You,” positioned as **Primary Track 3: Guidance, Pathways and Opportunity**. RSS discovery supports Track 1; checkpoints and reminders support Track 2. Programme context and track positioning are the owner’s description.

## Who it helps

Meet Amina Demo. We assume she is 23, lives in Nakuru, works part-time in retail, uses an entry-level Android phone on prepaid data, prefers English with a Kiswahili option, and wants a junior data role. These are a demo persona’s assumptions, not research findings or measured impact. See [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md).

The intended journey connects a short reading task to a checkpoint, an unlocked skill and a possible next step. The seeded Amina journey is covered by `test_onboard_complete_checkpoint_and_get_whats_next` in [the learner API tests](backend/learners/tests/test_api.py).

## Quick start

Use Windows PowerShell, Python 3.12.15, Node 24.21.0 LTS and pnpm 12.11.2, pinned in [.python-version](.python-version), [.node-version](.node-version) and [frontend/package.json](frontend/package.json). Python 3.12 remains the contributor-guide baseline; the exact Node pin replaces the older minimum for this task. Earlier Python 3.13.7/Node 22 validation remains historical in [the log](docs/PLANS.md).

Configuration requires process-level `SOMA_ENV` and an explicit `DATABASE_URL`. Other names are `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` and `SOMA_SENDER`. Optional sandbox configuration uses `AFRICASTALKING_USERNAME` and `AFRICASTALKING_API_KEY`; delivery is stubbed. See [.env.example](.env.example), [settings](backend/soma/settings.py) and [senders](backend/engagement/senders.py). No provider credentials are needed for the console demo.

**PowerShell — clone**

```powershell
git clone https://github.com/michael-mathenge/soma-i.git
Set-Location soma-i
```

Install the pinned Node version from [official Node downloads](https://nodejs.org/en/download). An existing Python with pip bootstraps uv 0.13.1 into ignored local tooling below; uv downloads portable Python 3.12.15 without Windows registration or a global interpreter change. See [uv Python distribution provenance](https://docs.astral.sh/uv/concepts/python-versions/#managed-python-distributions). Check versions and run setup from the repository root:

Create an isolated SQLite database under the OS temporary directory. Stop if temporary-directory creation fails; do not use a repository database. Keep this setup window open so the backend window can reuse the printed database URL. Development settings come from `.env`; the explicit `DATABASE_URL` below overrides its database setting. Copy `.env.example` only when `.env` does not already exist.

**PowerShell — prepare environment and seed temporary database**

```powershell
$ErrorActionPreference = 'Stop'
$env:SOMA_ENV = 'development'
python --version
node --version
python -m pip install --target .local/tooling uv==0.13.1
$setupUv = Join-Path (Get-Location) '.local/tooling/bin/uv.exe'
& $setupUv python install 3.12.15 --install-dir .local/python --no-bin --no-registry
if ($LASTEXITCODE -ne 0) { throw "Portable Python installation failed." }
& $setupUv venv .venv --python .local/python/cpython-3.12.15-windows-x86_64-none/python.exe --seed
if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
./.venv/Scripts/Activate.ps1
python -c "import sys; assert sys.prefix != sys.base_prefix, 'Project virtual environment is not active'; print(sys.executable)"
python -c "import sys; assert sys.version_info[:3] == (3, 12, 15), 'Use the pinned Python runtime'"
python -m pip install --require-hashes -r requirements.lock
if ($LASTEXITCODE -ne 0) { throw "Locked dependency installation failed." }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$setupDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("somai-setup-" + [guid]::NewGuid())
try { New-Item -ItemType Directory -Path $setupDirectory -ErrorAction Stop | Out-Null } catch { throw "Temporary database directory could not be created; stop setup." }
$env:DATABASE_URL = "sqlite:///" + (Join-Path $setupDirectory "demo.sqlite3").Replace('\', '/')
$env:SOMA_SENDER = 'console'
Write-Output $env:DATABASE_URL
python backend/manage.py migrate
if ($LASTEXITCODE -ne 0) { throw "Migrations failed; stop setup." }
Write-Output $env:DATABASE_URL
python backend/manage.py seed_demo
if ($LASTEXITCODE -ne 0) { throw "Demo seed failed; stop setup." }
```

If PowerShell blocks activation, run this in the same window, then retry activation and the virtual-environment check. The same session-only policy step can address npm script-policy blocking in its window.

**PowerShell — session-only script-policy troubleshooting**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

In a frontend PowerShell window, select the cloned repository root when prompted, then start Vite. This window does not run database commands and needs no database configuration.

**PowerShell — frontend**

```powershell
$ErrorActionPreference = 'Stop'
$repositoryRoot = Read-Host "Enter the full path to the cloned soma-i repository"
Set-Location -LiteralPath $repositoryRoot -ErrorAction Stop
Set-Location frontend
npx --yes pnpm@12.11.2 install --frozen-lockfile
npx --yes pnpm@12.11.2 run dev
```

In a backend PowerShell window, select the same repository root and paste the exact `DATABASE_URL` printed by setup when prompted. Verify that its temporary database exists before starting Django.

**PowerShell — backend using setup database**

```powershell
$ErrorActionPreference = 'Stop'
$repositoryRoot = Read-Host "Enter the full path to the cloned soma-i repository"
Set-Location -LiteralPath $repositoryRoot -ErrorAction Stop
$env:SOMA_ENV = 'development'
$env:DATABASE_URL = Read-Host "Paste the DATABASE_URL printed by setup"
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $env:DATABASE_URL.StartsWith('sqlite:///')) { throw "Use the setup SQLite URL." }
$databasePath = [System.IO.Path]::GetFullPath($env:DATABASE_URL.Substring(10))
if (-not $databasePath.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $databasePath -PathType Leaf)) { throw "Use the existing setup database under the OS temporary directory." }
$env:SOMA_SENDER = 'console'
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py runserver
```

Open the Vite URL printed by the frontend command and select **Open the demo learner**
(in Kiswahili: **Fungua mwanafunzi wa majaribio**). The labels are defined in the [English](frontend/src/i18n/en.json) and [Kiswahili](frontend/src/i18n/sw.json) translations.

The test server ignores an inherited `PYTHON` value unless it names an existing file; see [Python resolution](backend/python-resolution.mjs), fixed in commit `e2f0296`.

For backend checks, use the setup PowerShell window at the repository root with its temporary `DATABASE_URL` still set:

**PowerShell — backend checks**

```powershell
$env:SOMA_ENV = 'test'
$env:DJANGO_DEBUG = 'false'
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe -m pytest backend
```

For frontend checks, use the frontend window in `frontend`. Playwright creates its own isolated OS-temp SQLite database and prints its URL. Free ports 8127 and 4177 before running it: inspect any listeners, then stop the owning servers in their original windows. Do not stop an unfamiliar process. Server reuse is disabled in the config, so `PW_REUSE_SERVER` has no effect.

**PowerShell — frontend checks with installed Chrome**

```powershell
$env:SOMA_ENV = 'test'
$env:DJANGO_DEBUG = 'false'
npx --yes pnpm@12.11.2 run test:e2e:guard
npx --yes pnpm@12.11.2 run test:e2e:robustness
npx --yes pnpm@12.11.2 run lint
npx --yes pnpm@12.11.2 run build
netstat -ano -p tcp | Select-String ':8127 |:4177 '
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npx --yes pnpm@12.11.2 exec playwright test --timeout=60000
```

`PLAYWRIGHT_CHANNEL=chrome` uses installed Google Chrome. To use Playwright's Chromium instead, remove the channel variable and install that browser if it is missing:

**PowerShell — optional Playwright Chromium**

```powershell
Remove-Item Env:PLAYWRIGHT_CHANNEL -ErrorAction SilentlyContinue
npx --yes pnpm@12.11.2 exec playwright install chromium
npx --yes pnpm@12.11.2 exec playwright test --timeout=60000
```

On Windows, a locked temporary database can produce a cleanup warning after teardown retries; an otherwise successful run still exits successfully.

To ingest live feeds or preview due reminders, use the setup window at the repository root with its temporary database URL:

**PowerShell — ingestion and console reminders**

```powershell
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py ingest_feeds
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe backend/manage.py send_reminders
```

Tests use local XML fixtures and do not require network access. Set `DATABASE_URL` to a PostgreSQL URL and configure the matching driver for a later database switch.

The 2026-10-12 entry in [docs/PLANS.md](docs/PLANS.md) records fresh temporary-database migrations, seed and startup checks, 117 backend tests passing, 16 guard tests passing with one skip, 14 robustness tests passing, lint, a 106.2 KB build, and 16 Playwright tests passing with exit code 0. Playwright used installed Chrome and child-only folder-valued `PYTHON`; teardown emitted the expected temporary-database warning. The log also records an interrupted sandbox-command limitation and items not tested, including Python 3.12 environment creation and interactive setup prompts.

## How it works

### RSS and skills

[The registry](backend/content/feeds.json) contains 11 feeds. Configuration-driven rules match content to pathways and skills, then rank beginner suitability. [The ingestion tests](backend/content/tests/test_ingestion.py) cover malformed feeds, missing dates, deduplication, HTML stripping, unsafe links, timeouts and ETag/Last-Modified handling. [SOURCES.md](docs/SOURCES.md) records source checks and attribution; those are historical checks, not guarantees of current availability.

The [canonical pathways](backend/pathways/constants.py) are:

| Pathway | Skills |
|---|---|
| Data Analyst | Spreadsheets, SQL, Data Visualisation, Statistics |
| Frontend Developer | HTML, CSS, JavaScript, Accessibility, Git |
| Backend/Python Developer | Python, Git, API Development, Testing |

Git uses one shared skill record. Learners can skip, restart or switch pathways; see `test_skip_restart_switch_and_delete_are_available`.

`seed_demo` uses committed fixtures and hand-written items without fetching live feeds. Hand-written Data Analyst items carry “(demo)” and the source “SOMA.i sample content”; developer fixture items carry “(sample content).” See `test_seed_demo_handwritten_samples_share_one_source_and_distinct_links` and `test_seed_demo_fixture_picks_are_offline_low_data_and_labeled`. Opening external lessons still requires connectivity.

### Reminders, skill and schedule

`send_reminders` uses the console sender for this demo; real SMS delivery is not implemented. The dry-run option previews due reminders without sending or creating reminder records. See [the command](backend/engagement/management/commands/send_reminders.py) and `test_send_reminders_dry_run_sends_and_logs_nothing`.

The reusable [SOMA.i Reminder Ops skill](.agents/skills/soma-reminder-ops/SKILL.md) calls `reminder_ops`: a database-read workflow with 24-hour repeat suppression and a JSONL log restricted to `.local/` or the OS temporary directory. It refuses both repository database paths. See `test_reminder_ops_refuses_repository_database_paths`, `test_reminder_ops_suppresses_repeats_until_cooldown_expires` and `test_reminder_ops_rejects_log_path_outside_local_or_temp`.

The skill permits at most one Gmail digest draft and forbids sending messages or reading mail. The helper has mocked coverage in `test_gmail_draft_helper_only_creates_a_draft`; the live Gmail step is **not tested**.

[The scheduled-task record](docs/SCHEDULED_TASK.md) documents two failed scheduled attempts, followed by a successful run after working-directory and log-permission fixes. The hourly schedule was then paused. It requires the machine and Codex app to stay open; its database copy can become stale.

## Demo script

This is a suggested demo sequence derived from the seed, API and browser tests; no app screen was inspected during this documentation plan.

1. Open the seeded Amina Demo learner in English and use the Data Analyst pathway.
2. Follow a recommended lesson, return and submit the three-question checkpoint.
3. Inspect the returned unlocked skill, next checkpoint, reading recommendations and labelled sample opportunities.
4. Switch to Kiswahili to demonstrate the available interface translation, then inspect reminder preferences.
5. Explain the reusable reminder skill and the documented successful scheduled run; the schedule is paused and Gmail was not exercised.

The checkpoint journey has test coverage in `test_onboard_complete_checkpoint_and_get_whats_next` and the Playwright test “onboard and complete a checkpoint in English and Swahili.” Amina is seeded part-way through Data Analyst with English weekly reminders enabled; see `test_seed_demo_is_repeatable_and_opts_amina_into_english_weekly_reminders`.

Offline reload is **not tested** and is not part of this demo promise. [PLANS.md](docs/PLANS.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [DECISIONS.md](docs/DECISIONS.md) and [SOURCES.md](docs/SOURCES.md) provide supporting project records.

## Container image

The repository builds a single image that serves the application, the API and
the static assets from one origin, so session cookies and CSRF stay
same-origin.

**PowerShell — build and run against PostgreSQL**

```powershell
docker compose up --build
```

**PowerShell — build and run against a temporary SQLite file**

```powershell
docker build -t soma-i:local .
docker run --rm -p 8000:8000 -e SOMA_ENV=development -e DATABASE_URL=sqlite:////tmp/soma.sqlite3 -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 -e DJANGO_DEBUG=false -e DJANGO_HSTS_SECONDS=0 soma-i:local
```

The image runs migrations on start, serves on port 8000 and has a health
check on `/api/health/`. The application runs as an unprivileged user and the
image contains only the locked requirements.

This is the production-shaped image, not a deployed service. Hosting, DNS,
TLS, backups and the release gates recorded in
[FREE_TIER_VERIFICATION.md](docs/FREE_TIER_VERIFICATION.md) are still
outstanding, and no public deployment has been made.

## Serve it for review

Two ways to get the project running locally. The container is the quickest
and matches the production image; the development servers give you hot
reload while you work.

### Option 1: the container

One command. It serves the application, the API and the assets from a
single origin on <http://127.0.0.1:8000>.

**PowerShell — build and run**

```powershell
docker build -t soma-i:local .
docker run --rm -p 8000:8000 -e SOMA_ENV=development -e DATABASE_URL=sqlite:////tmp/soma.sqlite3 -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 -e DJANGO_DEBUG=false -e DJANGO_HSTS_SECONDS=0 soma-i:local
```

**PowerShell — check it came up**

```powershell
curl.exe -s http://127.0.0.1:8000/api/health/
```

The expected reply is `{"status":"ok","service":"soma.i"}`. Then open
<http://127.0.0.1:8000/catalogue>.

To use PostgreSQL instead, `docker compose up --build` starts the
application and a database together.

### Option 2: the development servers

Use this when you want to change the code and see the change without
rebuilding an image. It needs two windows.

**PowerShell — window one, the backend**

```powershell
Set-Location C:\dev\soma-i
$env:SOMA_ENV = 'development'
$env:DJANGO_DEBUG = 'true'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1'
$env:DATABASE_URL = 'sqlite:///C:/Users/' + $env:USERNAME + '/AppData/Local/Temp/soma-dev/dev.sqlite3'
New-Item -ItemType Directory -Force -Path "$env:TEMP\soma-dev" | Out-Null
.\.venv\Scripts\python.exe backend\manage.py migrate --noinput
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

**PowerShell — window two, the frontend**

```powershell
Set-Location C:\dev\soma-irontend
npx --yes pnpm@12.11.2 install --frozen-lockfile
npx --yes pnpm@12.11.2 run dev
```

Then open <http://127.0.0.1:5173/catalogue>.

### If a port is already in use

Port 8000 is commonly taken by another service. The frontend proxy target
and the development port are both configurable, so point them somewhere
free.

**PowerShell — window one, the backend on another port**

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8010 --noreload
```

**PowerShell — window two, the frontend pointed at it**

```powershell
$env:SOMAI_API_ORIGIN = 'http://127.0.0.1:8010'
$env:SOMAI_FRONTEND_PORT = '5175'
npx --yes pnpm@12.11.2 run dev
```

Then open <http://127.0.0.1:5175/catalogue>.

## Built with Codex

Codex assisted with planning, implementation, tests, documentation, and
debugging, including Windows Playwright cleanup and Python resolution.
This repository contains AI-assisted code. Changes were developed through
scoped requests and checked using backend tests, node:test suites, lint,
production builds, and Playwright runs. Test results demonstrate the
checked scenarios; they do not establish production readiness or validate
the product assumptions with real learners.

The following workflow account is mine as the project owner; repository commits verify the artifacts, not which assistant authored each line.

I chose the idea, Amina’s assumed learner profile, Primary Track 3, the three pathways and the boundaries: no real SMS, accounts, live opportunity aggregation or deployment. I decided which review findings to fix, accept or defer.

I used Plan mode first, four-part prompts, one task per chat and read-only reviews of named commit ranges. Planning, prompts and review notes were drafted with Claude; implementation code was written with Codex. [AGENTS.md](AGENTS.md) records working rules developed from mistakes.

Confirmed artifacts include the Django/DRF backend, React/Vite frontend, migrations and tests (`5d8e4e6`); RSS ingestion (`cadb257`); the reminder command and skill (`a2e289b`, `1b6afde`); repository-database protection (`ade65fe`); and scheduled-task documentation (`0d3d56e`).

One review found that a corrupt reminder log line could block later runs. Commit `647e611` tolerates malformed lines and reports warnings; `test_reminder_ops_skips_corrupt_middle_log_line_and_warns` covers that case.

One incident shaped the safeguards: a Codex probe fell back through `.env` to the repository-root database and changed demo data. This is my account of the incident. The resulting contributor rules require explicit temporary databases; the e2e guard protects both repository paths, and reminder previews use dry run. Dry run is not a SQLite read-only connection flag.

[PLANS.md](docs/PLANS.md) records validation results and remaining evidence gaps.

Read the [AI-use disclosure](docs/AI-usage.md) for the owner’s account of AI contributions, decisions and limitations.

## Track and operating-constraint mapping

| Track or constraint | What the repository demonstrates | Remaining limit |
|---|---|---|
| Primary Track 3 | Ordered skills, checkpoints and next-step sample opportunities; learner API tests | Real opportunity aggregation: **not done** |
| Track 1 | Registered RSS sources, matching and ingestion tests | Source quality is curated, not independently certified |
| Track 2 | Checkpoints and bilingual console reminders; engagement tests | Real SMS: **not done** |
| Credibility | Attribution, original links, date provenance and stale-source handling; ingestion tests and SOURCES.md | External content is not independently fact-checked |
| Low bandwidth | Text-based lesson cards, pathway payload under 1,500 bytes in `test_pathways_list_omits_seeded_picks_and_stays_under_1500_bytes`, recorded build below 200 KB | “Low data” is a fixed flag, not measured usage; offline journey **not tested** |
| Accessibility and inclusion | Native controls, labels and navigation landmarks in App.jsx; skip/restart/switch API coverage | Full keyboard, contrast, screen-reader and plain-language audit: **not done** |
| Personalisation without exclusion | Pathway/skill recommendations and supported skip, restart and switch actions | Learning outcomes and recommendation quality have not been validated with learners |
| Privacy and security | Optional phone, deletion endpoint, feed-text stripping and link validation | Durable accounts and production access control: **not done** |
| Multilingual | English/Kiswahili interface and reminder strings; bilingual test definitions | Pathway-specific translation is limited to Data Analyst; native-speaker review **not done** |
| Local relevance | Kenya-labelled sample opportunities and the assumed Nakuru learner | Locally African RSS sources and verified local vacancies: **not done** |

## Publishing a curated curriculum

The automatic route needs two independent publishers whose reuse permission
is verified. A small learning site often has one publisher with generous
terms rather than two with narrow ones, so there is a second route: a
**curated curriculum**, where the owner checks each reading link by hand and
records the check.

The rules are deliberately strict even though the owner selects the links.
Every link is reviewed, dated and expires, and a link whose review has
expired is not served. A step needs at least three links and a topic needs
at least two independent publishers, so no single publisher can carry a
curriculum. Publication creates a new revision; a published curriculum is
frozen, and a later change creates a new version and leaves the old one
intact for the learners who selected it.

A curated link is published as its title, its publisher and its address.
No publisher text is reproduced, so there is no excerpt to republish. The
review records the publisher's own terms page, which is the evidence that
the material may be read and linked to.

The reviewed curricula live in
[backend/pathways/curricula.json](backend/pathways/curricula.json), beside
the reviewed discovery rules, so the whole curriculum is reviewed in one
place. Each entry records the link, the publisher, the publisher's own
terms page as the evidence, who checked it, the dates, and why it was
chosen:

```json
{
  "title": "How the web works",
  "url": "https://developer.mozilla.org/en-US/docs/Learn_web_development",
  "publisher": "MDN Web Docs",
  "evidence_url": "https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines",
  "reviewed_by": "Your name",
  "reviewed_on": "2026-10-21",
  "expires_on": "2026-12-20",
  "rationale": "Explains the request and response cycle."
}
```

Each step needs at least three links and each topic needs links from at
least two publishers. The learning sequence, the checkpoint criteria and
the check-in questions come from the reviewed discovery rules, so a curated
topic is the same kind of learning sequence as every other pathway. Only
the reading list comes from the curricula file.

**PowerShell — publish it**

```powershell
$env:SOMA_ENV = 'development'
$env:DATABASE_URL = 'sqlite:///C:/Users/' + $env:USERNAME + '/AppData/Local/Temp/soma-curated/curated.sqlite3'
New-Item -ItemType Directory -Force -Path "$env:TEMP\soma-curated" | Out-Null
.\.venv\Scripts\python.exe backend\manage.py migrate --noinput
.\.venv\Scripts\python.exe backend\manage.py publish_curriculum --dry-run
.\.venv\Scripts\python.exe backend\manage.py publish_curriculum
```

A dry run validates every link and reports what would be published without
writing anything. Pass a path to publish a different file.

## Recording review evidence

A pathway can only be published when the owner has confirmed, in writing and
with a date, that the material is freely accessible, in English, attributed,
and covered by a publisher whose reuse permission has been verified. The
pipeline has always required that evidence; these commands are how it is
recorded, so the review does not have to be written by hand into a database.

**PowerShell — approve a feed endpoint**

```powershell
$env:SOMA_ENV = 'development'
$reviews = "$env:TEMP\somai-feeds.json"
@'
{
  "feeds": [
    {
      "key": "fcc_sql",
      "reviewed_by": "Your name",
      "scope": "Title and link with attribution; excerpts are not republished.",
      "reviewed_on": "2026-10-21",
      "expires_on": "2026-12-20",
      "evidence_url": "https://www.freecodecamp.org/copyright/",
      "allowed_urls": ["https://www.freecodecamp.org/news/tag/sql/rss/"],
      "publisher_key": "freecodecamp",
      "excerpt_reuse": false
    }
  ]
}
'@ | Set-Content -Path $reviews -Encoding UTF8
.\.venv\Scripts\python.exe backend\manage.py approve_feeds $reviews --dry-run
```

**PowerShell — approve a publisher**

```powershell
$publishers = "$env:TEMP\somai-publishers.json"
@'
{
  "publishers": [
    {
      "key": "freecodecamp",
      "domains": ["freecodecamp.org"],
      "reviewed_by": "Your name",
      "reviewed_on": "2026-10-21",
      "expires_on": "2026-12-20",
      "evidence_url": "https://www.freecodecamp.org/copyright/",
      "independence_confirmed": true
    }
  ]
}
'@ | Set-Content -Path $publishers -Encoding UTF8
.\.venv\Scripts\python.exe backend\manage.py approve_publishers $publishers --dry-run
```

**PowerShell — review the ingested items**

```powershell
$items = "$env:TEMP\somai-items.json"
@'
{
  "items": [
    {
      "url": "https://www.freecodecamp.org/news/learn-sql-in-30-minutes/",
      "publisher_key": "freecodecamp",
      "author": "Author name",
      "reviewed_by": "Your name",
      "reviewed_on": "2026-10-21",
      "expires_on": "2026-12-20",
      "evidence_url": "https://www.freecodecamp.org/copyright/",
      "free_access": true,
      "english_confirmed": true
    }
  ]
}
'@ | Set-Content -Path $items -Encoding UTF8
.\.venv\Scripts\python.exe backend\manage.py review_resources $items --dry-run
```

Every command validates the whole file before it writes anything, refuses a
review that is not dated, current or shorter than ninety days, refuses a
publisher that shares a domain with another publisher, and never infers
permission from a licence string, a feed tag or a previous approval. Excerpt
reuse is a separate decision and is not granted unless you grant it; content
is published as title, publisher and date by default.

The reviewed files hold the owner's decisions, so keep them outside the
repository. `--dry-run` reports what would change without writing anything.

## Known limits

SOMA.i is a local proof of concept using anonymous sessions rather than
durable user accounts. Opportunities are labelled sample examples, not
live vacancies. Reminder delivery uses console output; production SMS
delivery, deployment, and live opportunity aggregation are outside scope.

Offline support covers the cached app shell and previously viewed reading
data. Progress submissions require connectivity. The demo persona and
product assumptions still need validation with real learners.

On Windows, Playwright may leave its isolated temporary database behind
when the file remains locked. Teardown retries briefly, then warns without
failing an otherwise successful run.

- Amina and the retention problem are assumptions. Learner research and measured impact are **not done**; [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) makes no statistical claim.
- Recommendations remain thin for API Development and Testing. `test_seed_demo_fixture_picks_are_offline_low_data_and_labeled` accepts a minimum of one fixture pick for those skills, versus two for the others.
- Lesson cards hide reading minutes. “Low data” is a fixed content flag, not a bandwidth measurement; see the card-metadata test and ingestion code.
- English/Kiswahili interface support does not translate external lessons or all pathway-specific terminology. The app’s “ · hatua” checkpoint gloss needs native-speaker review; see `App.jsx`.
- Opportunity percentages compare one supplied unlocked skill with the listing’s skills. A “100% match” is not a hiring probability or a measure of overall job readiness; see [matching.py](backend/opportunities/matching.py).
- Service-worker caching exists, but offline reload is **not tested**. No offline progress-submission queue is implemented in [sw.js](frontend/public/sw.js).
- The scheduled task is documented as paused. Copies can become stale, overlapping runs can duplicate alerts or drafts, and live Gmail drafting is **not tested**.
- Real SMS, accounts, live opportunity aggregation and deployment are outside this capstone. Production privacy/security hardening is **not done**.
- At the 2026-10-12 checkpoint, PostgreSQL, Python 3.12 environment creation and interactive setup prompts were **not tested**. P1 below adds isolated Python 3.12 validation; hosted PostgreSQL and interactive fresh-clone prompts remain not tested. The earlier setup/startup evidence stays historical.

Licensed under the MIT License; see [LICENSE](LICENSE).


## P1 reproducible dependency baseline - 2026-10-14

- Runtime pins: Python 3.12.15 (security-maintenance line), Node 24.21.0 LTS and pnpm 12.11.2. Windows x64 execution is validated; Linux/macOS, hosted PostgreSQL and deployment are not tested by P1. The guide's Python 3.12 baseline is retained. Portable Python comes from Astral python-build-standalone, not an official python.org Windows installer. The local tooling bootstrap requires an existing Python/pip; it does not install uv or Python globally. Existing environments should be preserved until a separately created environment passes checks.
- requirements.txt pins direct requirements. requirements.lock pins resolved transitive versions and SHA256 hashes, generated by uv 0.13.1 with Python 3.12 universal resolution. That resolution includes platform markers/artifact hashes; it is not execution evidence for other platforms. Install from the hash-checked lock, not a new unconstrained resolution. Django moves from unsupported 5.1 to 5.2.18 LTS. Black stays pinned as a contributor tool but was not run; formatting remains owner-controlled.
- The tracked pnpm-lock.yaml is the frontend lock of record. Direct versions and package-manager version are exact; engineStrict and strictPeerDependencies reject mismatches. Use the no-global-install npx command above; its version bootstrap was checked on Node 24.21.0. Do not use npm install in frontend, regenerate package-lock.json or commit the pre-existing untracked npm lock. P1 validation used ignored isolated copies rather than upgrading the existing .venv. The validation log records a separate concurrent npm install in the original frontend; its untracked lockfile is excluded from this PR.
- pnpm 12 recorded exact release-age exceptions for @playwright/test, playwright and playwright-core 1.64.1 during resolution. These are narrow, visible pins for the current Playwright release, not an exemption for all future versions. The frozen install, advisory check and browser suite are recorded in docs/PLANS.md. An advisory check cannot establish that a package is free of undisclosed vulnerabilities.
- ESLint 10 keeps the existing rules-of-hooks error and exhaustive-deps warning explicitly. The hooks plugin's newer React Compiler diagnostics are not silently added as part of a dependency-only change. Application source/tests are unchanged. Vite's explicit es2020 target/proxy is retained. CSS minification is disabled to preserve authored custom-property token values after Vite 8's default minifier shortened six-digit white to #fff, which the unchanged contrast test cannot parse. This preserves the existing palette/test contract; browser compatibility beyond the exercised Chrome suite is not claimed.
- Re-lock deliberately after reviewing support/security guidance, then rerun validation. Sources checked 2026-10-14: [Django support](https://www.djangoproject.com/download/), [Python support/releases](https://www.python.org/downloads/), [Node releases](https://nodejs.org/en/about/previous-releases), [Vite support](https://vite.dev/releases), [Vite migration](https://vite.dev/guide/migration), [ESLint 10 migration](https://eslint.org/docs/latest/use/migrate-to-10.0.0), [pnpm frozen installation](https://pnpm.io/cli/install) and [uv locking](https://docs.astral.sh/uv/pip/compile/). Exact package releases were checked through PyPI/npm metadata. Full results, limits and unchanged historical setup evidence are in docs/PLANS.md; P1 does not clear O1/C1 or authorize release.


## P2 explicit environment configuration - 2026-10-14

Set SOMA_ENV in the process before any Django command. Accepted values are development, test, staging and production; an omitted/unknown value stops startup. A .env file cannot select the environment. Only development/test may read it, and existing process values win. Staging/production ignore .env entirely, so copying local defaults cannot enable debug or choose a repository database there. The current commands above set the environment explicitly; older command-only examples elsewhere require this environment setup too.

| Setting | Local development/test | Staging/production |
|---|---|---|
| DATABASE_URL | Required absolute OS-temp SQLite file; relative paths, memory URIs, query options and repository targets are refused | Required PostgreSQL hostname/database/credentials; sslmode=verify-full and sslrootcert=system or an absolute CA path; bounded connect_timeout; duplicate/unknown options are refused |
| DJANGO_SECRET_KEY | Local-only fallback permitted; empty values refused | Explicit non-development value, at least 50 characters and five distinct characters; operator must generate a separate random secret |
| DJANGO_DEBUG | Defaults true only in development, false in test; strict true/false parsing | Must be false; malformed values stop startup |
| DJANGO_ALLOWED_HOSTS | Defaults localhost,127.0.0.1,testserver | Required exact lower-case DNS names; no wildcard, scheme, port or local/IP target |
| DJANGO_CSRF_TRUSTED_ORIGINS | Empty by default; exact configured-host HTTP/HTTPS origins if supplied | Empty by default for same-origin operation; supplied origins must be exact HTTPS origins on allowed hosts, without paths or wildcard |
| DJANGO_TRUST_PROXY_SSL_HEADER | False; cannot be enabled locally | False by default. Enable only after verifying that the sole ingress strips/replaces client forwarding headers and the application cannot be reached around it |
| DJANGO_HSTS_SECONDS | Must be 0 | Defaults 3600; explicit range 0-31536000. includeSubDomains and preload stay false for this existing multipurpose domain |

The checks parse PostgreSQL configuration without connecting. They do not verify credentials, provider eligibility, mounted CA files, DNS, actual TLS/proxy behavior, database identity/least privilege or hosted isolation. Hosted commands still require the separately reviewed target-allowlist workflow in AGENTS.md; P2 supplies no permission to probe hosted learner data. A missing CA file or invalid certificate must fail on a future connection rather than downgrade verification. Live validation remains a later gate.

Deployed settings enable HTTPS redirects, Secure/HttpOnly/SameSite=Lax session cookies, Secure/SameSite=Lax CSRF cookies, nosniff, same-origin referrer policy and frame denial. Forwarded-host trust stays off. The CSRF cookie retains Django's readable default for future same-origin token handling; P2 does not implement account ownership or API-wide CSRF enforcement (P3), request limits (P5), or private service-worker cache isolation (P6). Existing anonymous API behavior is preserved.

STATIC_ROOT is the ignored .local/static directory for later collection. P2 does not provide a production web server, frontend SPA/static serving, ingress or deployment. Security-tag deployment tests intentionally retain security.W005 and security.W021 because subdomain HSTS/preload are not enabled before existing-domain review; this is not a claim that all deployment checks or release gates are cleared.

Validation names/counts and failed sandbox-temp setup attempts are recorded in docs/PLANS.md. Configuration tests use synthetic .invalid PostgreSQL URLs and block socket/psycopg connections. HTTP tests exercise middleware with signed-cookie test sessions, not hosted learner data. Actual database-backed checks use printed OS-temp SQLite only. Official guidance checked 2026-10-14: [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [proxy trust](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header) and [PostgreSQL certificate verification](https://www.postgresql.org/docs/current/libpq-ssl.html). O1/C1 remain blocked; P2 is not release approval.

## Optional accounts and ownership preview - 2026-10-14

P3 adds the optional **Account** page alongside guest learning. This is an unreleased preview: email ownership is unverified, verification/recovery delivery is unavailable until P4, shared request limits remain P5, and O1/C1 still block activation. Use synthetic credentials for local rehearsals. No email is sent.

Registration uses a trimmed, lowercased email address with database-enforced case-insensitive uniqueness and a Django-hashed password of 12-128 characters, checked against Django's similarity/common/numeric validators. One nullable account owner is added to each learner profile; the migration leaves existing profiles and progress unowned and preserves IDs. Evidence: `test_registration_hashes_password_normalizes_email_and_rotates_session`, `test_duplicate_email_rejected_atomically_and_database_enforces_case_uniqueness` and `test_migration_preserves_guest_profile_and_progress` in [account tests](backend/learners/tests/test_accounts.py).

Choose **Attach this guest profile and its progress** explicitly during registration to retain the current guest's learning records under the new account. Without that choice, the old guest row remains unowned and the new account starts without a pathway. Signing in restores the account profile and ends this browser's previous guest session; separate guest data is retained but is not merged or recoverable through a new guest session. Guest retention/cleanup remains a later operations concern. Signing out ends the account session while retaining durable progress. Evidence: `test_explicit_attachment_preserves_progress_ids`, `test_registration_without_attachment_preserves_unowned_guest`, `test_login_restores_owner_ignores_foreign_guest_and_session_id`, and `test_logout_flushes_session_and_owner_remains_durable`.

Profile/progress endpoints resolve the current owner from Django's server session, ignoring submitted learner/owner IDs and stale guest IDs for owned profiles. Authenticated profile deletion via Settings is rejected; use **Account → Delete account and progress**, confirm the current password and accept the confirmation dialog. Deletion cascades through that user's account/profile records; another account survives. Evidence: `test_guest_cannot_reuse_attached_profile`, `test_two_accounts_isolate_profile_writes_and_deletion` and `test_progress_writes_restart_and_cascade_deletion_resolve_current_owner`.

Unsafe API requests require CSRF even before login, including guest onboarding and demo selection. Direct API clients must GET `/api/csrf/` with the same cookie jar and send its `csrf_token` as `X-CSRFToken` on writes. Login/register/logout return a fresh token after rotation. The browser bootstraps/refreshes tokens and never automatically retries a write. Only Django session authentication is enabled; no browser-stored bearer credentials. Evidence: `test_anonymous_unsafe_routes_require_csrf`, `test_wrong_token_and_cross_origin_rejected`, `test_authenticated_csrf_required_and_old_token_rejected`, and [account browser tests](frontend/tests/accounts.spec.js). Shared seeded demo selection is restricted to development/test and cannot be used while authenticated or attached through the new demo session flow (`test_shared_demo_cannot_attach_or_be_used_by_account`, `test_demo_disabled_outside_local_modes`).

Private API responses send `Cache-Control: private, no-store`. The new public-shell service worker purges legacy caches and does not intercept/cache API requests. Account requests require its version acknowledgement when a worker controls the page; an old worker blocks account use until updated/reloaded. Evidence: `test_private_api_never_cacheable_and_identity_excludes_credentials`, `new offline worker purges private legacy caches and never caches API data`, and `legacy controlling worker blocks account requests until updated`. Offline private progress is unavailable; broader public metadata caching and offline checks remain P6. Cross-tab UI synchronization and remote device erasure are not claimed.

Official implementation references checked 2026-10-14: [Django session login/logout](https://docs.djangoproject.com/en/5.2/topics/auth/default/) and [DRF session authentication and anonymous-login CSRF requirements](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication). Actual results, intermediate failures and untested limits are in [the P3 log](docs/PLANS.md). Hosted PostgreSQL concurrency, live verification/recovery, rate limiting, real accounts, deployment and public release are not tested or authorized by P3.

## Offline verification and recovery foundation - 2026-10-14

P4 adds an offline implementation; **live email delivery and P4 activation remain BLOCKED**. The default SOMA_ACCOUNT_EMAIL_MODE=disabled exposes unavailable notices and rejects requests/confirmation with 503. Only development/test may opt into memory mode. Startup rejects memory in staging/production and rejects SMTP/Brevo/console mode names. Even if ordinary Django EMAIL_BACKEND is set elsewhere, account previews explicitly select Django's in-memory backend. No provider adapter or credentials are included. Evidence: test_unsupported_delivery_modes_never_issue_tokens, test_deployed_runtime_never_enables_memory_delivery, test_settings_reject_deployed_preview_without_database_connection and test_preview_uses_fixed_fragment_link_and_explicit_memory_backend in [recovery tests](backend/learners/tests/test_recovery.py).

Use only synthetic local accounts in memory mode. Preview messages remain in the server process's Django mail outbox: they are not sent, printed, written to files or exposed through an API. They disappear with that process. Their fixed local link destination is http://127.0.0.1:4177; this is a fixture/preview origin, not a production URL or proof of domain control. The preview does not create a background job, retry queue, notification promise or durable outbox. Evidence: test_preview_uses_fixed_fragment_link_and_explicit_memory_backend and test_memory_delivery_failure_rolls_back_token_and_never_exposes_secret.

In memory mode, a signed-in unverified owner can request a verification preview from Account. Anonymous recovery requests use the normalized email and produce the same response for unknown, malformed, inactive and unverified addresses; only an active account with a dated verified address can receive a reset preview. Timing indistinguishability and request-rate protection are not claimed; shared limits remain P5. Opening a link does not change account state. Explicit CSRF-protected confirmation is required. Verification does not sign anyone in, and password reset requires a valid 12-128-character password, invalidates other Django sessions through the changed password hash and never logs the learner in automatically. Evidence: test_verification_request_uses_current_owner_not_supplied_email, test_recovery_request_is_generic_for_unknown_unverified_inactive_and_malformed, test_verification_stores_only_hash_and_requires_explicit_post, test_csrf_required_on_all_recovery_writes and test_reset_changes_password_invalidates_sessions_and_never_auto_logs_in.

Each random 256-bit token is stored only as a SHA-256 digest, with purpose, a keyed digest of relevant account state, expiry and consumption timestamp. Verification expires in 24 hours; reset expires in 30 minutes. Replacement revokes previous tokens of that purpose; confirmation consumes all outstanding tokens for the account. Email/password/verification-state changes, inactivity, deletion, wrong-purpose use, tampering, expiry and replay reject the token. Invalid passwords leave a valid reset token available for an explicit correction. Token rows are retained until account deletion or future retention work; no automatic token cleanup is implemented. Evidence: test_expiry_and_replacement_make_old_tokens_unusable, test_wrong_purpose_foreign_user_and_token_tampering_rejected, test_account_state_changes_invalidate_token and test_reset_rejects_weak_password_without_consuming_token. PostgreSQL concurrency validation remains P7.

Preview links place the token in the URL fragment; the confirmation screen removes the fragment from browser history before its capability request, holds it only in component memory, and sends it in the explicit confirmation POST body. It never renders the token or stores it in browser storage. Browser reload after scrubbing needs a fresh link; there is no automatic replay. English recovery labels are language-marked in the experimental Kiswahili interface. Evidence: disabled delivery stays unavailable and fragment is scrubbed without a write, verification requires an explicit confirmation and never displays the token, reset pending prevents duplicate writes and success requires explicit sign in, and mobile reset labels remain readable and English-marked in [browser tests](frontend/tests/account-recovery.spec.js).

The nullable verification-date/token migration preserves existing account/profile identity and leaves previous accounts unverified (test_recovery_migration_preserves_identity_owner_and_profile_data). The earlier P3 unavailable statements above describe that checkpoint; staging/production delivery is still unavailable. [OWASP recovery guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) was checked 2026-10-14 as design guidance, not a claim of complete security compliance. [Provider gates](docs/FREE_TIER_VERIFICATION.md) and [actual validation](docs/PLANS.md) remain authoritative. No live email, provider eligibility, real-user recovery, hosted database, deployment or public release has been tested.
