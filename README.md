# SOMA.i — learning that leads somewhere

SOMA.i connects curated RSS learning content to goal-based pathways, checkpoints, reminders and sample opportunities. It is a proof of concept for the Andela x OpenAI x MIVA Codex Accelerator theme, “Learning That Stays With You,” positioned as **Primary Track 3: Guidance, Pathways and Opportunity**. RSS discovery supports Track 1; checkpoints and reminders support Track 2. Programme context and track positioning are the owner’s description.

## Who it helps

Meet Amina Demo. We assume she is 23, lives in Nakuru, works part-time in retail, uses an entry-level Android phone on prepaid data, prefers English with a Kiswahili option, and wants a junior data role. These are a demo persona’s assumptions, not research findings or measured impact. See [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md).

The intended journey connects a short reading task to a checkpoint, an unlocked skill and a possible next step. The seeded Amina journey is covered by `test_onboard_complete_checkpoint_and_get_whats_next` in [the learner API tests](backend/learners/tests/test_api.py).

## Quick start

Use Windows PowerShell, Python 3.12 and Node 20 or newer. The contributor guide specifies these versions; [the validation log](docs/PLANS.md) also records checks with Python 3.13.7.

Configuration names are `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` and `SOMA_SENDER`. Optional sandbox configuration uses `AFRICASTALKING_USERNAME` and `AFRICASTALKING_API_KEY`; delivery is stubbed. See [.env.example](.env.example), [settings](backend/soma/settings.py) and [senders](backend/engagement/senders.py). No provider credentials are needed for the console demo.

**PowerShell — clone**

```powershell
git clone https://github.com/michael-mathenge/soma-i.git
Set-Location soma-i
```

Install Python 3.12 and Node 20 or newer. Check the installed versions, then run setup from the repository root:

Create an isolated SQLite database under the OS temporary directory. Stop if temporary-directory creation fails; do not use a repository database. Keep this setup window open so the backend window can reuse the printed database URL. Development settings come from `.env`; the explicit `DATABASE_URL` below overrides its database setting. Copy `.env.example` only when `.env` does not already exist.

**PowerShell — prepare environment and seed temporary database**

```powershell
$ErrorActionPreference = 'Stop'
python --version
node --version
py -3.12 -m venv .venv
./.venv/Scripts/Activate.ps1
python -c "import sys; assert sys.prefix != sys.base_prefix, 'Project virtual environment is not active'; print(sys.executable)"
python -m pip install -r requirements.txt
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
npm install
npm run dev
```

In a backend PowerShell window, select the same repository root and paste the exact `DATABASE_URL` printed by setup when prompted. Verify that its temporary database exists before starting Django.

**PowerShell — backend using setup database**

```powershell
$ErrorActionPreference = 'Stop'
$repositoryRoot = Read-Host "Enter the full path to the cloned soma-i repository"
Set-Location -LiteralPath $repositoryRoot -ErrorAction Stop
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
Write-Output $env:DATABASE_URL
./.venv/Scripts/python.exe -m pytest backend
```

For frontend checks, use the frontend window in `frontend`. Playwright creates its own isolated OS-temp SQLite database and prints its URL. Free ports 8127 and 4177 before running it: inspect any listeners, then stop the owning servers in their original windows. Do not stop an unfamiliar process. Server reuse is disabled in the config, so `PW_REUSE_SERVER` has no effect.

**PowerShell — frontend checks with installed Chrome**

```powershell
npm run test:e2e:guard
npm run test:e2e:robustness
npm run lint
npm run build
netstat -ano -p tcp | Select-String ':8127 |:4177 '
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:e2e
```

`PLAYWRIGHT_CHANNEL=chrome` uses installed Google Chrome. To use Playwright's Chromium instead, remove the channel variable and install that browser if it is missing:

**PowerShell — optional Playwright Chromium**

```powershell
Remove-Item Env:PLAYWRIGHT_CHANNEL -ErrorAction SilentlyContinue
npx playwright install chromium
npm run test:e2e
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
- The current PostgreSQL path, Python 3.12 environment creation and interactive setup prompts are **not tested**; the fresh setup/startup and automated checks listed above were run on 2026-10-12.

Licensed under the MIT License; see [LICENSE](LICENSE).
